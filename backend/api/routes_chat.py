# -*- coding: utf-8 -*-
"""
routes_chat.py — Чат-бот аналитик ТИТАН

POST /api/chat — вопрос к LLM по загруженным данным ТОРО.
Контекст формируется из ТEXX же функций что обслуживают вкладки:
фильтры, risk_scoring_v2, агрегаты, финансы, виды работ, плановики и т.д.
Поддержка: DeepSeek API (приоритет) → Ollama Qwen3 4B (фоллбек).
"""

import json
import os
import re
import httpx
import pandas as pd
import numpy as np

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2, is_empty_eo_mask
from config.constants import METHODS_RISK, ВНЕПЛАНОВЫЕ_ВИДЫ


# ── Загрузка .env ──

def _load_env():
    for p in [os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
              os.path.join(os.path.dirname(__file__), "..", ".env")]:
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())

_load_env()

router = APIRouter(prefix="/api", tags=["chat"])

# ── Конфигурация LLM ──

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:4b"

DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}

# Классификация оборудования (из routes_equipment.py)
EQUIPMENT_CLASSES = [
    ('Насос', r'насос|нгн|нцс|цнс|нпс|pump'),
    ('Компрессор', r'компрессор|компр|кмп|compr'),
    ('Ёмкость', r'ёмкость|емкость|бак|резервуар|сепаратор|отстойник'),
    ('Теплообменник', r'теплообменник|т/о|тепл|хо|холодильник|конденсатор|подогреватель'),
    ('Колонна', r'колонна|абсорбер|десорбер|скруббер|ректификац'),
    ('Арматура', r'арматура|задвижка|клапан|затвор|кран|вентиль'),
    ('Трубопровод', r'трубопровод|трубопр|линия|коллектор'),
    ('Электродвигатель', r'электродвигатель|эл\.двигатель|э/двиг|двигатель|мотор'),
    ('КИП', r'кип|датчик|преобразователь|манометр|термометр|расходомер|уровнемер'),
]


def _classify_equipment(text):
    """Определить класс оборудования по тексту."""
    if not text or str(text).strip() in ('', 'Н/Д', 'nan', 'None'):
        return 'Без класса'
    text_lower = str(text).lower()
    for name, pattern in EQUIPMENT_CLASSES:
        if re.search(pattern, text_lower):
            return name
    return 'Прочее'


def _sf(v):
    """Безопасное преобразование в float."""
    if pd.isna(v) or v is None:
        return 0.0
    return float(v)


def _fmt(val):
    """Форматирование числа с пробелами."""
    return f"{val:,.0f}".replace(",", " ")


SYSTEM_PROMPT_TEMPLATE = """\
Ты — аудитор-аналитик системы ТИТАН Аудит ТОРО. Отвечаешь на русском языке.
Ты анализируешь данные технического обслуживания и ремонтов (ТОРО) нефтегазового предприятия.

Вот ПОЛНАЯ аналитическая сводка по текущим данным (с учётом активных фильтров и порогов):

{context}

Правила:
- Отвечай кратко и по делу
- Ссылайся на конкретные цифры из данных
- Если вопрос вне контекста данных — скажи что не имеешь информации
- Используй термины ТОРО: заказ, ЕО (единица оборудования), ТМ (техническое место), план/факт
- При упоминании сумм используй форматирование с пробелами (1 234 567 руб.)
- При анализе рисков объясняй что значит каждый метод\
"""

FALLBACK_MESSAGE = (
    "LLM-модель не подключена. Для работы чата установите Ollama и модель Qwen3 4B.\n"
    "Команды:\n"
    "```\ncurl -fsSL https://ollama.com/install.sh | sh\n"
    "ollama pull qwen3:4b\n```"
)


# ── Pydantic-схемы ──

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[ChatMessage] = []
    filters: str = "{}"
    thresholds: str = "{}"


class ChatResponse(BaseModel):
    reply: str
    llm_available: bool


# ── Формирование ПОЛНОГО контекста из данных (как на вкладках) ──

def _build_full_context(session_id: str, filters_str: str, thresholds_str: str) -> str:
    """Формирует полный аналитический контекст для LLM.

    Переиспользует ту же логику что и вкладки:
    фильтрация → агрегаты → risk_scoring_v2 → сводки по секциям.
    """
    session = get_session(session_id)
    if not session:
        return "Данные не загружены."

    df = session['df']

    # Разбор фильтров
    try:
        f = json.loads(filters_str)
    except Exception:
        f = {}
    try:
        thresh = {**DEFAULT_THRESHOLDS, **json.loads(thresholds_str)}
    except Exception:
        thresh = DEFAULT_THRESHOLDS

    # Применяем фильтры (те же что во вкладках)
    hierarchy = f.get('hierarchy', {})
    extra = {k: v for k, v in f.items() if k != 'hierarchy'}
    df_f = apply_hierarchy_filters(df, hierarchy)
    df_f = apply_extra_filters(df_f, extra)

    # Агрегаты и скоринг v2
    agg = compute_aggregates(df_f)
    df_scored, scoring_info = apply_risk_scoring_v2(df_f, agg, thresh)

    lines = []

    # ═══ 1. KPI ═══
    total = len(df_scored)
    plan = _sf(df_scored['Plan_N'].sum())
    fact = _sf(df_scored['Fact_N'].sum())
    dev = fact - plan
    dev_pct = (dev / plan * 100) if plan else 0

    risk_orders = df_scored[df_scored['Priority_Score'] > 0]
    risk_count = len(risk_orders)
    risk_pct = risk_count / max(total, 1) * 100

    completeness = _sf(df_scored['Data_Completeness'].mean()) if 'Data_Completeness' in df_scored.columns else 0

    lines.append("═══ ОБЩИЕ KPI ═══")
    lines.append(f"Всего заказов: {total}")
    lines.append(f"План (сумма): {_fmt(plan)} руб.")
    lines.append(f"Факт (сумма): {_fmt(fact)} руб.")
    lines.append(f"Отклонение: {'+' if dev > 0 else ''}{_fmt(dev)} руб. ({dev_pct:+.1f}%)")
    lines.append(f"Заказов с риском: {risk_count} ({risk_pct:.1f}%)")
    lines.append(f"Средняя полнота данных: {completeness:.1f}%")

    # Перерасход / экономия
    overrun = df_scored[df_scored['Fact_N'] > df_scored['Plan_N']]
    savings = df_scored[df_scored['Fact_N'] < df_scored['Plan_N']]
    lines.append(f"Заказов с перерасходом: {len(overrun)}")
    lines.append(f"Заказов с экономией: {len(savings)}")

    # ═══ 2. РИСК-СКОРИНГ (вкладка Приоритеты аудита) ═══
    lines.append("")
    lines.append("═══ РИСК-СКОРИНГ (6 методов) ═══")

    for method_name, method_info in METHODS_RISK.items():
        flag = f"S_{method_name}"
        score_col = f"Score_{method_name}"

        # Для C2-M2 исключаем заказы без ЕО
        if 'C2-M2' in method_name and flag in df_scored.columns:
            eo_c = 'EQUNR_Код' if 'EQUNR_Код' in df_scored.columns else 'ЕО'
            if eo_c in df_scored.columns:
                valid = ~is_empty_eo_mask(df_scored[eo_c])
                cnt = int((df_scored[flag] & valid).sum())
            else:
                cnt = int(df_scored[flag].sum())
        else:
            cnt = int(df_scored[flag].sum()) if flag in df_scored.columns else 0

        avg_score = _sf(df_scored[score_col].mean()) if score_col in df_scored.columns else 0
        threshold_val = thresh.get(method_name, method_info['threshold_default'])
        lines.append(f"  {method_name}: {cnt} заказов (порог={threshold_val}, ср.балл={avg_score:.1f})")

    # Категории риска
    if 'Risk_Category' in df_scored.columns:
        cats = df_scored['Risk_Category'].value_counts().to_dict()
        lines.append("")
        lines.append("Категории риска:")
        for cat in ['Красный', 'Жёлтый', 'Серый', 'Зелёный']:
            cnt = cats.get(cat, 0)
            if cnt > 0:
                lines.append(f"  {cat}: {cnt} заказов")

    # ═══ 3. ФИНАНСЫ (вкладка Финансы) ═══
    lines.append("")
    lines.append("═══ ФИНАНСЫ ═══")

    # ABC-анализ
    if 'ABC' in df_scored.columns:
        abc_stats = df_scored.groupby('ABC').agg(
            count=('ID', 'count'), fact_sum=('Fact_N', 'sum')
        ).reset_index()
        total_fact_abc = abc_stats['fact_sum'].sum()
        lines.append("ABC-распределение:")
        for _, r in abc_stats.sort_values('fact_sum', ascending=False).iterrows():
            pct = r['fact_sum'] / max(total_fact_abc, 1) * 100
            lines.append(f"  {r['ABC']}: {int(r['count'])} заказов, {_fmt(r['fact_sum'])} руб. ({pct:.1f}%)")

    # TOP-5 цехов по перерасходу
    if 'ЦЕХ' in df_scored.columns:
        ceh = df_scored.groupby('ЦЕХ').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        ceh['dev'] = ceh['fact'] - ceh['plan']
        ceh = ceh[ceh['ЦЕХ'] != 'Н/Д']
        top_ceh = ceh.sort_values('dev', ascending=False).head(5)
        if len(top_ceh) > 0:
            lines.append("TOP-5 цехов по отклонению:")
            for _, r in top_ceh.iterrows():
                lines.append(f"  {r['ЦЕХ']}: {int(r['count'])} заказов, отклонение {'+' if r['dev']>0 else ''}{_fmt(r['dev'])} руб.")

    # TOP-5 ТМ по перерасходу
    if 'ТМ' in df_scored.columns:
        tm = df_scored.groupby('ТМ').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        tm['dev'] = tm['fact'] - tm['plan']
        top_tm = tm.sort_values('dev', ascending=False).head(5)
        if len(top_tm) > 0:
            lines.append("TOP-5 ТМ по перерасходу:")
            for _, r in top_tm.iterrows():
                lines.append(f"  {r['ТМ']}: {int(r['count'])} заказов, отклонение {'+' if r['dev']>0 else ''}{_fmt(r['dev'])} руб.")

    # ═══ 4. ВИДЫ РАБОТ (вкладка Виды работ) ═══
    if 'Вид' in df_scored.columns:
        lines.append("")
        lines.append("═══ ВИДЫ РАБОТ ═══")
        vid_stats = df_scored.groupby('Вид').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        vid_stats['dev'] = vid_stats['fact'] - vid_stats['plan']

        # Определяем внеплановые
        if 'Вид_Код' in df_scored.columns:
            vid_codes = df_scored.groupby('Вид')['Вид_Код'].first().to_dict()
        else:
            vid_codes = {}

        for _, r in vid_stats.sort_values('count', ascending=False).iterrows():
            vid_code = vid_codes.get(r['Вид'], '')
            unplanned = ' [внеплановый]' if vid_code in ВНЕПЛАНОВЫЕ_ВИДЫ else ''
            lines.append(f"  {r['Вид']}{unplanned}: {int(r['count'])} заказов, факт {_fmt(r['fact'])} руб., откл {'+' if r['dev']>0 else ''}{_fmt(r['dev'])} руб.")

        # Внеплановые итого
        if vid_codes:
            unpl_mask = df_scored['Вид_Код'].isin(ВНЕПЛАНОВЫЕ_ВИДЫ) if 'Вид_Код' in df_scored.columns else pd.Series(False, index=df_scored.index)
            unpl_count = int(unpl_mask.sum())
            lines.append(f"Внеплановых заказов: {unpl_count} ({unpl_count / max(total, 1) * 100:.1f}%)")

    # ═══ 5. ПЛАНОВИКИ (вкладка Плановики) ═══
    if 'INGRP' in df_scored.columns:
        lines.append("")
        lines.append("═══ ПЛАНОВИКИ ═══")
        ingrp = df_scored.groupby('INGRP').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        ingrp['dev'] = ingrp['fact'] - ingrp['plan']
        for _, r in ingrp.sort_values('dev', ascending=False).head(5).iterrows():
            lines.append(f"  {r['INGRP']}: {int(r['count'])} заказов, откл {'+' if r['dev']>0 else ''}{_fmt(r['dev'])} руб.")

    # ═══ 6. РАБОЧИЕ МЕСТА (вкладка Раб.места) ═══
    if 'РМ' in df_scored.columns:
        lines.append("")
        lines.append("═══ РАБОЧИЕ МЕСТА ═══")
        rm = df_scored.groupby('РМ').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        rm['dev'] = rm['fact'] - rm['plan']
        rm = rm[rm['РМ'] != 'Н/Д']
        lines.append(f"Всего рабочих мест: {len(rm)}")
        top_rm = rm.sort_values('dev', ascending=False).head(5)
        for _, r in top_rm.iterrows():
            lines.append(f"  {r['РМ']}: {int(r['count'])} заказов, откл {'+' if r['dev']>0 else ''}{_fmt(r['dev'])} руб.")

    # ═══ 7. ОБОРУДОВАНИЕ ═══
    eo_col = 'ЕО' if 'ЕО' in df_scored.columns else None
    if eo_col:
        lines.append("")
        lines.append("═══ ОБОРУДОВАНИЕ ═══")

        # Классификация
        classes = df_scored[eo_col].map(_classify_equipment).value_counts()
        if len(classes) > 0:
            lines.append("По классам оборудования:")
            for cls, cnt in classes.head(8).items():
                if cls != 'Без класса':
                    lines.append(f"  {cls}: {cnt} заказов")
            no_class = classes.get('Без класса', 0)
            if no_class > 0:
                lines.append(f"  Без класса (ЕО не определено): {no_class}")

        # TOP-5 ЕО по стоимости
        equnr_col = 'EQUNR_Код' if 'EQUNR_Код' in df_scored.columns else eo_col
        has_eo = ~is_empty_eo_mask(df_scored[equnr_col])
        df_eo = df_scored[has_eo]
        if len(df_eo) > 0:
            eo_stats = df_eo.groupby(equnr_col).agg(
                count=('ID', 'count'), fact=('Fact_N', 'sum')
            ).reset_index()
            top_eo = eo_stats.sort_values('fact', ascending=False).head(5)
            lines.append("TOP-5 оборудования по стоимости:")
            for _, r in top_eo.iterrows():
                lines.append(f"  {r[equnr_col]}: {int(r['count'])} заказов, факт {_fmt(r['fact'])} руб.")

    # ═══ 8. TOP-10 ПРИОРИТЕТНЫХ ЗАКАЗОВ ═══
    score_col = 'Priority_Score'
    if score_col in df_scored.columns:
        lines.append("")
        lines.append("═══ TOP-10 ПРИОРИТЕТНЫХ ЗАКАЗОВ (по Priority_Score) ═══")
        top10 = df_scored.nlargest(10, score_col)
        for _, r in top10.iterrows():
            oid = r.get('ID', '?')
            ps = _sf(r.get('Priority_Score', 0))
            dq = _sf(r.get('DQ_Risk', 0))
            fact_val = _sf(r.get('Fact_N', 0))
            plan_val = _sf(r.get('Plan_N', 0))
            cat = r.get('Risk_Category', '?')
            methods_cnt = int(r.get('Methods_Count', 0))

            # Сработавшие методы
            triggered = []
            for mn in METHODS_RISK.keys():
                flag_col = f"S_{mn}"
                if flag_col in r.index and r[flag_col]:
                    triggered.append(mn.split(':')[0])

            methods_str = ', '.join(triggered) if triggered else 'нет'
            lines.append(
                f"  {oid}: PS={ps:.1f} DQ={dq:.1f} кат={cat} методы=[{methods_str}] "
                f"факт={_fmt(fact_val)} план={_fmt(plan_val)}"
            )

    # ═══ 9. КАЧЕСТВО ДАННЫХ ═══
    lines.append("")
    lines.append("═══ КАЧЕСТВО ДАННЫХ ═══")
    lines.append(f"Средняя полнота данных: {completeness:.1f}%")

    check_fields = ['Plan_N', 'Начало', 'Конец', 'ТМ', 'ЕО', 'ABC', 'Вид']
    for field in check_fields:
        if field in df_scored.columns:
            if field == 'Plan_N':
                empty = int((df_scored[field].fillna(0) == 0).sum())
            elif field in ('Начало', 'Конец'):
                empty = int(df_scored[field].isna().sum())
            else:
                empty = int(
                    df_scored[field].astype(str).str.strip().isin(
                        {'Н/Д', 'н/д', 'Не присвоено', 'nan', 'NaN', 'None', 'none', '', ' ', '0', 'Пусто'}
                    ).sum()
                )
            if empty > 0:
                pct = empty / max(total, 1) * 100
                lines.append(f"  {field}: не заполнено у {empty} заказов ({pct:.1f}%)")

    # ═══ 10. АКТИВНЫЕ ФИЛЬТРЫ ═══
    active_filters = []
    if hierarchy:
        for level, vals in hierarchy.items():
            if vals:
                active_filters.append(f"{level}: {', '.join(str(v) for v in vals)}")
    if extra.get('search'):
        active_filters.append(f"Поиск: {extra['search']}")
    if extra.get('vid'):
        active_filters.append(f"Виды: {', '.join(extra['vid'])}")
    if extra.get('abc'):
        active_filters.append(f"ABC: {', '.join(extra['abc'])}")
    if extra.get('stat'):
        active_filters.append(f"Статус: {', '.join(extra['stat'])}")

    if active_filters:
        lines.append("")
        lines.append("═══ АКТИВНЫЕ ФИЛЬТРЫ ═══")
        for af in active_filters:
            lines.append(f"  {af}")
        lines.append(f"(Показано {total} из {len(df)} заказов)")
    else:
        lines.append("")
        lines.append("Фильтры: не применены (все данные)")

    return "\n".join(lines)


# ── Проверка доступности Ollama ──

async def _check_ollama() -> bool:
    """Проверить доступность Ollama."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def _query_deepseek(messages: list[dict]) -> str:
    """Отправить запрос к DeepSeek API."""
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": DEEPSEEK_MODEL, "messages": messages, "max_tokens": 2000, "temperature": 0.3}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _query_ollama(messages: list[dict]) -> str:
    """Отправить запрос к Ollama и получить ответ."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "Нет ответа от модели.")


# ── Эндпоинт ──

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Чат с аналитиком ТИТАН по данным ТОРО."""
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена.")

    # Полный контекст с учётом фильтров и порогов (как на вкладках)
    context = _build_full_context(req.session_id, req.filters, req.thresholds)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.history[-20:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    # Приоритет: DeepSeek API → Ollama → заглушка
    if DEEPSEEK_API_KEY:
        try:
            reply = await _query_deepseek(messages)
            return ChatResponse(reply=reply, llm_available=True)
        except Exception as e:
            print(f"[Chat] DeepSeek error: {e}")

    if await _check_ollama():
        try:
            reply = await _query_ollama(messages)
            return ChatResponse(reply=reply, llm_available=True)
        except Exception as e:
            print(f"[Chat] Ollama error: {e}")

    return ChatResponse(
        reply="LLM недоступна. Проверьте DeepSeek API ключ или Ollama.",
        llm_available=False,
    )


@router.get("/chat/status")
async def chat_status():
    """Статус доступности LLM-провайдеров."""
    has_ds = bool(DEEPSEEK_API_KEY)
    has_ol = await _check_ollama()
    return {
        "available": has_ds or has_ol,
        "provider": "deepseek" if has_ds else ("ollama" if has_ol else "none"),
    }
