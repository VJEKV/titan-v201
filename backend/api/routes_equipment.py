# -*- coding: utf-8 -*-
"""
api/routes_equipment.py — GET /api/tab/equipment
Вкладка Оборудование: классификация, метрики по классам, TOP-50, heatmap, частота обслуживания.
"""

import json
import re
import pandas as pd
import numpy as np
from io import BytesIO
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2, _is_empty_eo, is_empty_eo_mask, EMPTY_EO_VALUES
from config.constants import METHODS_RISK, ВНЕПЛАНОВЫЕ_ВИДЫ

router = APIRouter()
DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}

MONTH_SHORT = {1:'Янв',2:'Фев',3:'Мар',4:'Апр',5:'Май',6:'Июн',7:'Июл',8:'Авг',9:'Сен',10:'Окт',11:'Ноя',12:'Дек'}

# Ключевые слова для классификации оборудования
EQUIPMENT_CLASSES = [
    ('Насос', r'насос|нгн|нцс|цнс|нпс|pump'),
    ('Компрессор', r'компрессор|компр|кмп|compr'),
    ('Ёмкость', r'ёмкость|емкость|бак|резервуар|сепаратор|отстойник|ёмк|емк'),
    ('Теплообменник', r'теплообменник|т/о|тепл|хо|холодильник|конденсатор|подогреватель'),
    ('Колонна', r'колонна|абсорбер|десорбер|скруббер|ректификац'),
    ('Реактор', r'реактор|регенератор'),
    ('Арматура', r'арматура|задвижка|клапан|затвор|кран|вентиль'),
    ('Трубопровод', r'трубопровод|трубопр|линия|коллектор|т/пр'),
    ('Электродвигатель', r'электродвигатель|эл\.двигатель|э/двиг|двигатель|мотор|электромотор'),
    ('КИП', r'кип|датчик|преобразователь|манометр|термометр|расходомер|уровнемер|контроллер'),
]


def _sf(v):
    """Safe float."""
    return 0.0 if pd.isna(v) else float(v)


def classify_equipment(text):
    """Определить класс оборудования по тексту."""
    if not text or str(text).strip() in EMPTY_EO_VALUES:
        return 'Без класса'
    text_lower = str(text).lower()
    for cls_name, pattern in EQUIPMENT_CLASSES:
        if re.search(pattern, text_lower):
            return cls_name
    return 'Прочее'


def _get_df(session_id, filters_str, thresholds_str):
    """Получить отфильтрованный DataFrame."""
    session = get_session(session_id)
    if not session:
        return None
    df = session['df']
    try:
        f = json.loads(filters_str)
    except Exception:
        f = {}
    try:
        thresh = {**DEFAULT_THRESHOLDS, **json.loads(thresholds_str)}
    except Exception:
        thresh = DEFAULT_THRESHOLDS
    hierarchy = f.get('hierarchy', {})
    extra = {k: v for k, v in f.items() if k != 'hierarchy'}
    df_f = apply_hierarchy_filters(df, hierarchy)
    df_f = apply_extra_filters(df_f, extra)
    agg = compute_aggregates(df_f)
    df_f, _ = apply_risk_scoring_v2(df_f, agg, thresh)
    return df_f


@router.get("/api/tab/equipment")
async def get_equipment(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки Оборудование."""
    df_f = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    # Определяем колонку ЕО
    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
    eo_name_col = 'ЕО' if 'ЕО' in df_f.columns else eo_col

    # Фильтруем заказы с реальным ЕО — жёсткая фильтрация
    df_f = df_f.copy()
    if eo_col in df_f.columns:
        has_eo = ~is_empty_eo_mask(df_f[eo_col])
    else:
        has_eo = pd.Series(False, index=df_f.index)

    df_with_eo = df_f[has_eo].copy()
    df_no_eo = df_f[~has_eo]

    # Классификация оборудования
    if eo_name_col in df_with_eo.columns:
        df_with_eo['Класс_ЕО'] = df_with_eo[eo_name_col].apply(classify_equipment)
    else:
        df_with_eo['Класс_ЕО'] = 'Без класса'

    # === 1. Метрики по классам ===
    classes_data = []
    if len(df_with_eo) > 0:
        cls_grp = df_with_eo.groupby('Класс_ЕО').agg(
            n_eo=(eo_col, 'nunique'),
            n_orders=('ID', 'count'),
            plan=('Plan_N', 'sum'),
            fact=('Fact_N', 'sum'),
        ).reset_index()
        cls_grp['dev'] = cls_grp['fact'] - cls_grp['plan']
        cls_grp = cls_grp.sort_values('fact', ascending=False)
        for _, r in cls_grp.iterrows():
            classes_data.append({
                "class_name": str(r['Класс_ЕО']),
                "n_eo": int(r['n_eo']),
                "n_orders": int(r['n_orders']),
                "plan": _sf(r['plan']),
                "fact": _sf(r['fact']),
                "dev": _sf(r['dev']),
            })

    # === 2. Метрики на единицу оборудования ===
    per_eo_data = []
    if len(df_with_eo) > 0:
        for cls in cls_grp.itertuples():
            n_eo = max(cls.n_eo, 1)
            per_eo_data.append({
                "class_name": str(cls.Класс_ЕО),
                "avg_orders": round(cls.n_orders / n_eo, 1),
                "avg_cost": round(_sf(cls.fact) / n_eo, 0),
                "avg_plan": round(_sf(cls.plan) / n_eo, 0),
            })

    # === 3. TOP-50 ЕО по затратам ===
    top50 = []
    if len(df_with_eo) > 0:
        eo_stats = df_with_eo.groupby(eo_col).agg(
            n_orders=('ID', 'count'),
            fact=('Fact_N', 'sum'),
            plan=('Plan_N', 'sum'),
            name=(eo_name_col, 'first'),
            cls=('Класс_ЕО', 'first'),
        ).reset_index()
        eo_stats['dev'] = eo_stats['fact'] - eo_stats['plan']
        eo_stats = eo_stats.sort_values('fact', ascending=False).head(50)
        for _, r in eo_stats.iterrows():
            top50.append({
                "eo": str(r[eo_col]),
                "name": str(r['name'])[:60],
                "class_name": str(r['cls']),
                "n_orders": int(r['n_orders']),
                "plan": _sf(r['plan']),
                "fact": _sf(r['fact']),
                "dev": _sf(r['dev']),
            })

    # === 4. Лидеры по внеплановым среди A и B ===
    ABC_AB_VALUES = {'A', 'B', 'Высококритичное', 'Оч.высокая/Особокрит', 'Оч.высокая', 'Особокритичное',
                     'Высокая', 'Средней критичности', 'Средняя', 'Средней крит.'}
    unplanned_leaders = []
    if 'Вид' in df_with_eo.columns and 'ABC' in df_with_eo.columns:
        df_ab = df_with_eo[df_with_eo['ABC'].isin(ABC_AB_VALUES)]
        if 'ВИД_КОД' in df_ab.columns:
            df_unpl = df_ab[df_ab['ВИД_КОД'].isin(ВНЕПЛАНОВЫЕ_ВИДЫ)]
        else:
            df_unpl = df_ab[df_ab['Вид'].str.contains('неплан|аварий|срочн', case=False, na=False)]
        if len(df_unpl) > 0:
            unpl_grp = df_unpl.groupby('Класс_ЕО').agg(
                n_orders=('ID', 'count'),
                fact=('Fact_N', 'sum'),
            ).reset_index().sort_values('n_orders', ascending=False)
            for _, r in unpl_grp.iterrows():
                unplanned_leaders.append({
                    "class_name": str(r['Класс_ЕО']),
                    "n_orders": int(r['n_orders']),
                    "fact": _sf(r['fact']),
                })

    # === 5. Heatmap: месяцы × ТОП-100 ЕО ===
    heatmap = []
    heatmap_eo_stats = {}  # Статистика по ЕО: кол-во заказов + сумма
    eo_names_map = {}
    date_col = None
    for col in ['Начало', 'Конец', 'Факт_Начало']:
        if col in df_with_eo.columns and df_with_eo[col].notna().any():
            date_col = col
            break

    if date_col and len(df_with_eo) > 0:
        # Считаем кол-во заказов и сумму затрат для каждого ЕО
        eo_agg = df_with_eo.groupby(eo_col).agg(
            n_orders=('ID', 'count'),
            total_fact=('Fact_N', 'sum'),
        ).reset_index()
        # ТОП-100 по количеству заказов (убывание)
        eo_agg_sorted = eo_agg.sort_values('n_orders', ascending=False).head(100)
        top100_eo = eo_agg_sorted[eo_col].tolist()
        # Маппинг ЕО код → наименование
        if eo_name_col in df_with_eo.columns and eo_name_col != eo_col:
            names = df_with_eo.groupby(eo_col)[eo_name_col].first()
            eo_names_map = {str(k): str(v)[:40] for k, v in names.items()}
        # Статистика для фронтенда
        for _, ea in eo_agg_sorted.iterrows():
            eo_code = str(ea[eo_col])
            eo_name = eo_names_map.get(eo_code, '')
            eo_label = f"{eo_code} {eo_name}".strip() if eo_name else eo_code
            heatmap_eo_stats[eo_label] = {
                "n_orders": int(ea['n_orders']),
                "total_fact": _sf(ea['total_fact']),
            }
        df_heat = df_with_eo[df_with_eo[eo_col].isin(top100_eo)].copy()
        df_heat['_month'] = df_heat[date_col].dt.month
        df_heat['_year'] = df_heat[date_col].dt.year
        df_valid = df_heat[df_heat['_month'].notna()]
        if len(df_valid) > 0:
            heat_grp = df_valid.groupby([eo_col, '_year', '_month'])['Fact_N'].sum().reset_index()
            for _, r in heat_grp.iterrows():
                eo_code = str(r[eo_col])
                eo_name = eo_names_map.get(eo_code, '')
                eo_label = f"{eo_code} {eo_name}".strip() if eo_name else eo_code
                heatmap.append({
                    "eo": eo_label,
                    "label": f"{MONTH_SHORT.get(int(r['_month']), '?')} {int(r['_year'])}",
                    "value": _sf(r['Fact_N']),
                })

    # === 6. Частота обслуживания ===
    frequency = []
    if date_col and len(df_with_eo) > 0:
        freq_cols = [eo_col, date_col]
        if eo_name_col and eo_name_col in df_with_eo.columns and eo_name_col != eo_col:
            freq_cols.append(eo_name_col)
        df_freq = df_with_eo[freq_cols].dropna(subset=[date_col]).copy()
        df_freq = df_freq.sort_values([eo_col, date_col])
        # Средний интервал между заказами на ЕО
        intervals = []
        for eo_id, grp in df_freq.groupby(eo_col):
            if len(grp) < 2:
                continue
            dates = grp[date_col].sort_values()
            diffs = dates.diff().dt.days.dropna()
            if len(diffs) > 0:
                avg_interval = diffs.mean()
                eo_name = ''
                if eo_name_col and eo_name_col in grp.columns and eo_name_col != eo_col:
                    eo_name = str(grp[eo_name_col].iloc[0])
                    if eo_name in ('Н/Д', 'nan', 'None', '', ' '):
                        eo_name = ''
                intervals.append({
                    "eo": str(eo_id),
                    "equipment_name": eo_name,
                    "n_orders": len(grp),
                    "avg_interval": round(avg_interval, 0),
                })
        intervals.sort(key=lambda x: x['avg_interval'])
        frequency = intervals[:30]

    # === 7. ABC-распределение ===
    abc_data = []
    if 'ABC' in df_f.columns:
        abc_stats = df_f.groupby('ABC').agg(
            count=('ID', 'count'), sum=('Fact_N', 'sum')
        ).reset_index()
        total_abc = abc_stats['sum'].sum()
        for _, r in abc_stats.sort_values('sum', ascending=False).iterrows():
            pct = r['sum'] / max(total_abc, 1) * 100
            abc_data.append({
                "abc": str(r['ABC']),
                "count": int(r['count']),
                "sum": _sf(r['sum']),
                "pct": round(pct, 1)
            })

    # === KPI ===
    total_eo = int(df_with_eo[eo_col].nunique()) if eo_col in df_with_eo.columns else 0
    abc_a = 0
    abc_b = 0
    no_class = 0
    avg_orders_per_eo = 0
    if total_eo > 0:
        avg_orders_per_eo = round(len(df_with_eo) / total_eo, 1)

    # Маппинг ABC: поддержка как кодов (A/B/C), так и текстовых описаний
    ABC_A_VALUES = {'A', 'Высококритичное', 'Оч.высокая/Особокрит', 'Оч.высокая', 'Особокритичное', 'Высокая'}
    ABC_B_VALUES = {'B', 'Средней критичности', 'Средняя', 'Средней крит.'}
    ABC_C_VALUES = {'C', 'Не критично', 'Низкой критичности'}

    abc_c = 0
    # Ищем по ABC (текст), потом по ABC_Код (код)
    for abc_col_name in ['ABC', 'ABC_Код']:
        if abc_col_name in df_with_eo.columns:
            vals = df_with_eo[abc_col_name].astype(str)
            abc_a_mask = vals.isin(ABC_A_VALUES)
            abc_b_mask = vals.isin(ABC_B_VALUES)
            abc_c_mask = vals.isin(ABC_C_VALUES)
            a_count = int(df_with_eo.loc[abc_a_mask, eo_col].nunique())
            b_count = int(df_with_eo.loc[abc_b_mask, eo_col].nunique())
            c_count = int(df_with_eo.loc[abc_c_mask, eo_col].nunique())
            if a_count > 0 or b_count > 0 or c_count > 0:
                abc_a = a_count
                abc_b = b_count
                abc_c = c_count
                break
    no_class = int(len(df_no_eo))

    return {
        "kpi": {
            "total_eo": total_eo,
            "abc_a": abc_a,
            "abc_b": abc_b,
            "abc_c": abc_c,
            "no_eo_orders": no_class,
            "avg_orders_per_eo": avg_orders_per_eo,
        },
        "abc_data": abc_data,
        "classes_data": classes_data,
        "per_eo_data": per_eo_data,
        "top50": top50,
        "unplanned_leaders": unplanned_leaders,
        "heatmap": heatmap,
        "heatmap_eo_stats": heatmap_eo_stats,
        "frequency": frequency,
    }


@router.get("/api/export/equipment-excel")
async def export_equipment_excel(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    eo: str = Query(""),
):
    """Выгрузка заказов по конкретному ЕО в Excel."""
    df_f = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
    if eo and eo_col in df_f.columns:
        df_export = df_f[df_f[eo_col].astype(str) == eo]
    else:
        df_export = df_f.head(0)

    cols = [c for c in ['ID', 'Текст', 'Вид', 'STAT', 'ABC', 'Plan_N', 'Fact_N', 'ТМ', 'ЕО', 'Начало', 'Конец'] if c in df_export.columns]
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export[cols].to_excel(writer, index=False, sheet_name=f'ЕО_{eo[:20]}')
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=EO_{eo[:20]}.xlsx"}
    )
