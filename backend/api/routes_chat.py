# -*- coding: utf-8 -*-
"""
routes_chat.py — Чат-бот аналитик ТИТАН

POST /api/chat — вопрос к LLM по загруженным данным ТОРО.
Заглушка при отсутствии Ollama, иначе отправляет в Qwen3 4B.
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from state.session import get_session
from config.constants import METHODS_RISK

router = APIRouter(prefix="/api", tags=["chat"])

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:4b"

SYSTEM_PROMPT_TEMPLATE = """\
Ты — аудитор-аналитик системы ТИТАН Аудит ТОРО. Отвечаешь на русском языке.
Ты анализируешь данные технического обслуживания и ремонтов (ТОРО) нефтегазового предприятия.

Вот сводка текущих данных:
{context}

Правила:
- Отвечай кратко и по делу
- Ссылайся на конкретные цифры из данных
- Если вопрос вне контекста данных — скажи что не имеешь информации
- Используй термины ТОРО: заказ, ЕО (единица оборудования), ТМ (техническое место), план/факт\
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


class ChatResponse(BaseModel):
    reply: str
    llm_available: bool


# ── Формирование контекста из DataFrame ──

def _build_context(df) -> str:
    """Сводка по загруженным данным для системного промпта."""
    lines = []

    # Общие KPI
    total = len(df)
    plan_sum = df['Plan_N'].sum() if 'Plan_N' in df.columns else 0
    fact_sum = df['Fact_N'].sum() if 'Fact_N' in df.columns else 0
    dev = fact_sum - plan_sum
    dev_pct = round(dev / plan_sum * 100, 1) if plan_sum else 0
    lines.append(f"Всего заказов: {total}")
    lines.append(f"План (сумма): {plan_sum:,.0f} руб.".replace(",", " "))
    lines.append(f"Факт (сумма): {fact_sum:,.0f} руб.".replace(",", " "))
    lines.append(f"Отклонение: {dev:+,.0f} руб. ({dev_pct:+.1f}%)".replace(",", " "))

    # Статистика по методам
    method_stats = []
    for method_name in METHODS_RISK:
        flag = f"S_{method_name}"
        if flag in df.columns:
            cnt = int(df[flag].sum())
            if cnt > 0:
                method_stats.append(f"  {method_name}: {cnt} заказов")
    if method_stats:
        lines.append("\nСработавшие методы риск-скоринга:")
        lines.extend(method_stats)

    # Категории риска
    if 'Risk_Category' in df.columns:
        cats = df['Risk_Category'].value_counts().to_dict()
        lines.append("\nКатегории риска:")
        for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {cnt}")
    elif 'Risk_Sum' in df.columns:
        risky = int((df['Risk_Sum'] > 0).sum())
        lines.append(f"\nЗаказов с риском: {risky} ({round(risky/total*100, 1)}%)")

    # Топ-5 аномальных заказов
    score_col = 'Priority_Score' if 'Priority_Score' in df.columns else 'Risk_Sum'
    if score_col in df.columns:
        id_col = 'ID' if 'ID' in df.columns else df.columns[0]
        top5 = df.nlargest(5, score_col)
        lines.append(f"\nТоп-5 аномальных заказов (по {score_col}):")
        for _, row in top5.iterrows():
            oid = row.get(id_col, '?')
            sc = row.get(score_col, 0)
            fact = row.get('Fact_N', 0)
            lines.append(f"  {oid}: score={sc:.1f}, факт={fact:,.0f}".replace(",", " "))

    # Топ-5 проблемных ЕО
    eo_col = 'ЕО' if 'ЕО' in df.columns else 'EQUNR_Код'
    if eo_col in df.columns:
        eo_counts = df[eo_col].value_counts().head(5)
        if not eo_counts.empty:
            lines.append("\nТоп-5 ЕО по количеству заказов:")
            for eo, cnt in eo_counts.items():
                lines.append(f"  {eo}: {cnt} заказов")

    # Топ-5 затратных ТМ
    if 'ТМ' in df.columns and 'Fact_N' in df.columns:
        tm_sum = df.groupby('ТМ')['Fact_N'].sum().nlargest(5)
        if not tm_sum.empty:
            lines.append("\nТоп-5 ТМ по фактическим затратам:")
            for tm, s in tm_sum.items():
                lines.append(f"  {tm}: {s:,.0f} руб.".replace(",", " "))

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
        raise HTTPException(status_code=404, detail="Сессия не найдена. Загрузите файл.")

    df = session['df']
    context = _build_context(df)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    # Проверяем Ollama
    available = await _check_ollama()
    if not available:
        return ChatResponse(reply=FALLBACK_MESSAGE, llm_available=False)

    # Формируем сообщения для LLM
    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.history[-20:]:  # Ограничиваем историю 20 сообщениями
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    try:
        reply = await _query_ollama(messages)
        return ChatResponse(reply=reply, llm_available=True)
    except Exception as e:
        return ChatResponse(
            reply=f"Ошибка при обращении к LLM: {str(e)}",
            llm_available=True,
        )
