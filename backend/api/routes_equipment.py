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
from utils.formatters import fmt_downtime
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
    ('Печь', r'печь|печи|печка|горелка|горелки|топка'),
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

    # Подготовка простоя — числовая колонка
    has_downtime = 'Простой_Сек' in df_with_eo.columns
    if has_downtime:
        df_with_eo['_dt_sec'] = pd.to_numeric(df_with_eo['Простой_Сек'], errors='coerce').fillna(0)

    # === 1. Метрики по классам ===
    classes_data = []
    if len(df_with_eo) > 0:
        agg_cls = {
            'n_eo': (eo_col, 'nunique'),
            'n_orders': ('ID', 'count'),
            'plan': ('Plan_N', 'sum'),
            'fact': ('Fact_N', 'sum'),
        }
        if has_downtime:
            agg_cls['downtime_sec'] = ('_dt_sec', 'sum')
        cls_grp = df_with_eo.groupby('Класс_ЕО').agg(**agg_cls).reset_index()
        cls_grp['dev'] = cls_grp['fact'] - cls_grp['plan']
        cls_grp = cls_grp.sort_values('fact', ascending=False)
        for _, r in cls_grp.iterrows():
            item = {
                "class_name": str(r['Класс_ЕО']),
                "n_eo": int(r['n_eo']),
                "n_orders": int(r['n_orders']),
                "plan": _sf(r['plan']),
                "fact": _sf(r['fact']),
                "dev": _sf(r['dev']),
            }
            if has_downtime:
                item["downtime_sec"] = _sf(r['downtime_sec'])
                item["downtime_fmt"] = fmt_downtime(r['downtime_sec'])
            classes_data.append(item)

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
    # Определяем колонку дат для отображения диапазона
    top_date_col = None
    for dc in ['Факт_Начало', 'Факт_Конец', 'Начало', 'Конец']:
        if dc in df_with_eo.columns and df_with_eo[dc].notna().any():
            top_date_col = dc
            break
    top_date_label = top_date_col or ''

    if len(df_with_eo) > 0:
        agg_dict = {
            'n_orders': ('ID', 'count'),
            'fact': ('Fact_N', 'sum'),
            'plan': ('Plan_N', 'sum'),
            'name': (eo_name_col, 'first'),
            'cls': ('Класс_ЕО', 'first'),
        }
        # ABC-критичность ЕО
        if 'ABC' in df_with_eo.columns:
            agg_dict['abc'] = ('ABC', 'first')
        # Даты
        if top_date_col:
            agg_dict['date_first'] = (top_date_col, 'min')
            agg_dict['date_last'] = (top_date_col, 'max')
        # Простой
        if has_downtime:
            agg_dict['downtime_sec'] = ('_dt_sec', 'sum')

        eo_stats = df_with_eo.groupby(eo_col).agg(**agg_dict).reset_index()
        eo_stats['dev'] = eo_stats['fact'] - eo_stats['plan']
        eo_stats = eo_stats.sort_values('fact', ascending=False).head(50)
        for _, r in eo_stats.iterrows():
            item = {
                "eo": str(r[eo_col]),
                "name": str(r['name'])[:60],
                "class_name": str(r['cls']),
                "n_orders": int(r['n_orders']),
                "plan": _sf(r['plan']),
                "fact": _sf(r['fact']),
                "dev": _sf(r['dev']),
            }
            if 'abc' in r.index and pd.notna(r['abc']):
                item['abc'] = str(r['abc'])
            else:
                item['abc'] = ''
            if 'date_first' in r.index and pd.notna(r['date_first']):
                item['date_first'] = r['date_first'].isoformat()[:10] if hasattr(r['date_first'], 'isoformat') else str(r['date_first'])[:10]
            else:
                item['date_first'] = ''
            if 'date_last' in r.index and pd.notna(r['date_last']):
                item['date_last'] = r['date_last'].isoformat()[:10] if hasattr(r['date_last'], 'isoformat') else str(r['date_last'])[:10]
            else:
                item['date_last'] = ''
            if has_downtime and 'downtime_sec' in r.index:
                item['downtime_sec'] = _sf(r['downtime_sec'])
                item['downtime_fmt'] = fmt_downtime(r['downtime_sec'])
            top50.append(item)

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
    # Пробуем все возможные колонки дат для частоты
    freq_date_col = None
    for col_candidate in ['Факт_Начало', 'Факт_Конец', 'Начало', 'Конец']:
        if col_candidate in df_with_eo.columns:
            # Пробуем конвертировать в datetime если ещё не datetime
            test_series = pd.to_datetime(df_with_eo[col_candidate], errors='coerce', dayfirst=True)
            non_null = test_series.notna().sum()
            if non_null > 0:
                freq_date_col = col_candidate
                break

    print(f"[FREQ DEBUG] date_col={date_col}, freq_date_col={freq_date_col}, df_with_eo len={len(df_with_eo)}")
    if freq_date_col:
        print(f"[FREQ DEBUG] dtype of {freq_date_col}: {df_with_eo[freq_date_col].dtype}")

    if freq_date_col and len(df_with_eo) > 0:
        freq_cols = [eo_col, freq_date_col]
        if eo_name_col and eo_name_col in df_with_eo.columns and eo_name_col != eo_col:
            freq_cols.append(eo_name_col)
        df_freq = df_with_eo[freq_cols].copy()
        # Принудительная конвертация дат
        df_freq['_freq_date'] = pd.to_datetime(df_freq[freq_date_col], errors='coerce', dayfirst=True)
        df_freq = df_freq.dropna(subset=['_freq_date'])
        df_freq = df_freq.sort_values([eo_col, '_freq_date'])

        # Диагностика
        eo_counts = df_freq.groupby(eo_col).size()
        eo_multi = (eo_counts >= 2).sum()
        print(f"[FREQ DEBUG] rows with valid date: {len(df_freq)}, unique EO: {len(eo_counts)}, EO with 2+ orders: {eo_multi}")

        # Сумма факт и план по каждому ЕО — для отображения в таблице частоты
        eo_fact_map = {}
        eo_plan_map = {}
        eo_abc_map = {}
        eo_date_first_map = {}
        eo_date_last_map = {}
        if 'Fact_N' in df_with_eo.columns:
            eo_fact_agg = df_with_eo.groupby(eo_col)['Fact_N'].sum()
            eo_fact_map = {str(k): _sf(v) for k, v in eo_fact_agg.items()}
        if 'Plan_N' in df_with_eo.columns:
            eo_plan_agg = df_with_eo.groupby(eo_col)['Plan_N'].sum()
            eo_plan_map = {str(k): _sf(v) for k, v in eo_plan_agg.items()}
        if 'ABC' in df_with_eo.columns:
            eo_abc_agg = df_with_eo.groupby(eo_col)['ABC'].first()
            eo_abc_map = {str(k): str(v) if pd.notna(v) else '' for k, v in eo_abc_agg.items()}
        if freq_date_col:
            dates_parsed = pd.to_datetime(df_with_eo[freq_date_col], errors='coerce', dayfirst=True)
            df_tmp = df_with_eo.copy()
            df_tmp['_parsed_date'] = dates_parsed
            date_min = df_tmp.groupby(eo_col)['_parsed_date'].min()
            date_max = df_tmp.groupby(eo_col)['_parsed_date'].max()
            for k, v in date_min.items():
                eo_date_first_map[str(k)] = v.isoformat()[:10] if pd.notna(v) and hasattr(v, 'isoformat') else ''
            for k, v in date_max.items():
                eo_date_last_map[str(k)] = v.isoformat()[:10] if pd.notna(v) and hasattr(v, 'isoformat') else ''

        # Средний интервал между заказами на ЕО
        intervals = []
        for eo_id, grp in df_freq.groupby(eo_col):
            if len(grp) < 2:
                continue
            dates = grp['_freq_date'].sort_values()
            diffs = dates.diff().dt.days.dropna()
            # Фильтруем нулевые и отрицательные интервалы
            diffs = diffs[diffs > 0]
            if len(diffs) > 0:
                avg_interval = diffs.mean()
                min_interval = diffs.min()
                max_interval = diffs.max()
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
                    "min_interval": round(min_interval, 0),
                    "max_interval": round(max_interval, 0),
                    "total_fact": eo_fact_map.get(str(eo_id), 0),
                    "total_plan": eo_plan_map.get(str(eo_id), 0),
                    "abc": eo_abc_map.get(str(eo_id), ''),
                    "date_first": eo_date_first_map.get(str(eo_id), ''),
                    "date_last": eo_date_last_map.get(str(eo_id), ''),
                })
        intervals.sort(key=lambda x: x['avg_interval'])
        frequency = intervals[:100]
        print(f"[FREQ DEBUG] frequency result count: {len(frequency)}")

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

    # Маппинг ABC: 4 уровня критичности
    ABC_OSOB_VALUES = {'Особокритичное', 'Оч.высокая/Особокрит', 'Оч.высокая'}  # Особо критичные
    ABC_VYSOK_VALUES = {'A', 'Высококритичное', 'Высокая'}  # Высоко критичные
    ABC_LOW_VALUES = {'B', 'Средней критичности', 'Средняя', 'Средней крит.', 'Низкой критичности'}  # Низкой критичности
    ABC_NONE_VALUES = {'C', 'Не критично'}  # Не критично

    abc_osob = 0
    abc_vysok = 0
    abc_low = 0
    abc_none = 0
    for abc_col_name in ['ABC', 'ABC_Код']:
        if abc_col_name in df_with_eo.columns:
            vals = df_with_eo[abc_col_name].astype(str)
            osob_count = int(df_with_eo.loc[vals.isin(ABC_OSOB_VALUES), eo_col].nunique())
            vysok_count = int(df_with_eo.loc[vals.isin(ABC_VYSOK_VALUES), eo_col].nunique())
            low_count = int(df_with_eo.loc[vals.isin(ABC_LOW_VALUES), eo_col].nunique())
            none_count = int(df_with_eo.loc[vals.isin(ABC_NONE_VALUES), eo_col].nunique())
            if osob_count > 0 or vysok_count > 0 or low_count > 0 or none_count > 0:
                abc_osob = osob_count
                abc_vysok = vysok_count
                abc_low = low_count
                abc_none = none_count
                break
    no_class = int(len(df_no_eo))

    return {
        "kpi": {
            "total_eo": total_eo,
            "abc_osob": abc_osob,
            "abc_vysok": abc_vysok,
            "abc_low": abc_low,
            "abc_none": abc_none,
            "no_eo_orders": no_class,
            "avg_orders_per_eo": avg_orders_per_eo,
        },
        "abc_data": abc_data,
        "classes_data": classes_data,
        "per_eo_data": per_eo_data,
        "top50": top50,
        "top_date_label": top_date_label,
        "freq_date_label": freq_date_col or '',
        "unplanned_leaders": unplanned_leaders,
        "heatmap": heatmap,
        "heatmap_eo_stats": heatmap_eo_stats,
        "frequency": frequency,
    }


@router.get("/api/equipment/orders")
async def get_equipment_orders(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    eo_code: str = Query(...),
):
    """Детализация заказов по конкретному ЕО для раскрывающегося списка TOP-50."""
    df_f = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
    df_eo = df_f[df_f[eo_col].astype(str) == str(eo_code)]

    orders = []
    for _, row in df_eo.iterrows():
        order_id = str(row.get('ID', '')) if pd.notna(row.get('ID')) else ''
        text = str(row.get('Текст', '')) if pd.notna(row.get('Текст')) else ''
        vid = str(row.get('Вид', '')) if pd.notna(row.get('Вид')) else ''
        # Приоритет: фактическая дата → плановая
        date_val = None
        for _dc in ['Факт_Начало', 'Факт_Конец', 'Начало', 'Конец']:
            v = row.get(_dc, None)
            if pd.notna(v):
                date_val = v
                break
        date_str = ''
        if pd.notna(date_val):
            date_str = date_val.isoformat()[:10] if hasattr(date_val, 'isoformat') else str(date_val)[:10]
        fact = _sf(row.get('Fact_N', 0))
        plan = _sf(row.get('Plan_N', 0))
        stat = str(row.get('STAT', '')) if pd.notna(row.get('STAT')) else ''
        # Каскадные даты
        date_source = str(row.get('Источник_Дат', 'NONE')) if pd.notna(row.get('Источник_Дат')) else 'NONE'
        ds_val = row.get('Дата_Начало')
        de_val = row.get('Дата_Конец')
        date_start_str = ds_val.strftime('%d.%m.%Y') if pd.notna(ds_val) and hasattr(ds_val, 'strftime') else ''
        date_end_str = de_val.strftime('%d.%m.%Y') if pd.notna(de_val) and hasattr(de_val, 'strftime') else ''
        rm = str(row.get('РМ', '')) if pd.notna(row.get('РМ')) else ''
        # Простой
        dt_sek = row.get('Простой_Сек', 0)
        dt_val = float(dt_sek) if pd.notna(dt_sek) else 0
        # Даты по сообщению
        ns_val = row.get('Сообщ_Начало')
        ne_val = row.get('Сообщ_Конец')
        ns_str = ns_val.strftime('%d.%m.%Y') if pd.notna(ns_val) and hasattr(ns_val, 'strftime') else ''
        ne_str = ne_val.strftime('%d.%m.%Y') if pd.notna(ne_val) and hasattr(ne_val, 'strftime') else ''
        orders.append({
            "id": order_id,
            "text": text,
            "vid": vid,
            "date": date_str,
            "fact": fact,
            "plan": plan,
            "dev": round(fact - plan, 2),
            "stat": stat,
            "date_start": date_start_str,
            "date_end": date_end_str,
            "date_source": date_source,
            "notify_start": ns_str,
            "notify_end": ne_str,
            "downtime_sec": dt_val,
            "downtime_fmt": fmt_downtime(dt_val),
            "rm": rm,
        })
    # Сортируем по дате (свежие сверху)
    orders.sort(key=lambda x: x['date'], reverse=True)
    return {"orders": orders}


@router.get("/api/equipment/by-class")
async def get_equipment_by_class(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    class_name: str = Query(...),
):
    """Список ЕО по классу оборудования с агрегатами."""
    df_f = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
    eo_name_col = 'ЕО' if 'ЕО' in df_f.columns else eo_col

    # Фильтруем заказы с реальным ЕО
    df_f = df_f.copy()
    if eo_col in df_f.columns:
        has_eo = ~is_empty_eo_mask(df_f[eo_col])
    else:
        has_eo = pd.Series(False, index=df_f.index)
    df_with_eo = df_f[has_eo].copy()

    # Классификация
    if eo_name_col in df_with_eo.columns:
        df_with_eo['Класс_ЕО'] = df_with_eo[eo_name_col].apply(classify_equipment)
    else:
        df_with_eo['Класс_ЕО'] = 'Без класса'

    # Фильтр по классу
    df_cls = df_with_eo[df_with_eo['Класс_ЕО'] == class_name]
    if len(df_cls) == 0:
        return {"items": []}

    # Группировка по ЕО
    agg_dict = {
        'n_orders': ('ID', 'count'),
        'plan': ('Plan_N', 'sum'),
        'fact': ('Fact_N', 'sum'),
        'name': (eo_name_col, 'first'),
    }
    if 'ABC' in df_cls.columns:
        agg_dict['abc'] = ('ABC', 'first')

    eo_grp = df_cls.groupby(eo_col).agg(**agg_dict).reset_index()
    eo_grp['dev'] = eo_grp['fact'] - eo_grp['plan']
    eo_grp = eo_grp.sort_values('fact', ascending=False)

    items = []
    for _, r in eo_grp.iterrows():
        items.append({
            "eo": str(r[eo_col]),
            "name": str(r['name'])[:60],
            "abc": str(r['abc']) if 'abc' in r.index and pd.notna(r['abc']) else '',
            "n_orders": int(r['n_orders']),
            "plan": _sf(r['plan']),
            "fact": _sf(r['fact']),
            "dev": _sf(r['dev']),
        })
    return {"items": items}


@router.get("/api/export/equipment-class-excel")
async def export_equipment_class_excel(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    class_name: str = Query(""),
    unplanned: bool = Query(False),
):
    """Выгрузка заказов по классу оборудования (опционально: только внеплановые)."""
    df_f = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
    eo_name_col = 'ЕО' if 'ЕО' in df_f.columns else eo_col

    # Фильтруем заказы с реальным ЕО
    df_f = df_f.copy()
    if eo_col in df_f.columns:
        has_eo = ~is_empty_eo_mask(df_f[eo_col])
    else:
        has_eo = pd.Series(False, index=df_f.index)
    df_with_eo = df_f[has_eo].copy()

    # Классификация
    if eo_name_col in df_with_eo.columns:
        df_with_eo['Класс_ЕО'] = df_with_eo[eo_name_col].apply(classify_equipment)
    else:
        df_with_eo['Класс_ЕО'] = 'Без класса'

    # Фильтр по классу
    if class_name:
        df_export = df_with_eo[df_with_eo['Класс_ЕО'] == class_name]
    else:
        df_export = df_with_eo

    # Фильтр внеплановых
    if unplanned:
        if 'ВИД_КОД' in df_export.columns:
            df_export = df_export[df_export['ВИД_КОД'].isin(ВНЕПЛАНОВЫЕ_ВИДЫ)]
        elif 'Вид' in df_export.columns:
            df_export = df_export[df_export['Вид'].str.contains('неплан|аварий|срочн', case=False, na=False)]

    cols = [c for c in ['ID', 'Текст', 'Вид', 'STAT', 'ABC', 'Plan_N', 'Fact_N', 'ТМ', 'ЕО', 'Начало', 'Конец'] if c in df_export.columns]
    safe_name = re.sub(r'[^\w\s-]', '', class_name)[:20] or 'class'
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export[cols].to_excel(writer, index=False, sheet_name=safe_name)
    output.seek(0)
    fname = f"{'Внеплан_' if unplanned else ''}{safe_name}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )


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
