# -*- coding: utf-8 -*-
"""
components/kpi_block.py — Блок ключевых показателей v112.5

st.html() вместо st.metric() — полный контроль размеров.
Внешний вид идентичен оригиналу: цвета, иконки, layout.
"""

import streamlit as st
import pandas as pd

from config.constants import HIERARCHY_LEVELS
from config.font_config import get_font_sizes
from utils.formatters import fmt, fmt_sign


def calculate_level_kpi(df_filtered, df_full=None):
    """Расчёт KPI для текущего уровня фильтрации."""
    kpi = {}
    kpi['orders_count'] = len(df_filtered)
    kpi['plan_sum'] = df_filtered['Plan_N'].sum() if 'Plan_N' in df_filtered.columns else 0
    kpi['fact_sum'] = df_filtered['Fact_N'].sum() if 'Fact_N' in df_filtered.columns else 0
    kpi['deviation'] = kpi['fact_sum'] - kpi['plan_sum']
    kpi['deviation_pct'] = (kpi['deviation'] / kpi['plan_sum'] * 100) if kpi['plan_sum'] > 0 else 0
    kpi['avg_cost'] = kpi['fact_sum'] / kpi['orders_count'] if kpi['orders_count'] > 0 else 0

    for level in HIERARCHY_LEVELS:
        key = level['key']
        if key in df_filtered.columns:
            kpi[f'{key}_count'] = df_filtered[key][df_filtered[key] != 'Н/Д'].nunique()
        else:
            kpi[f'{key}_count'] = 0

    if 'Risk_Sum' in df_filtered.columns:
        kpi['risk_sum'] = df_filtered['Risk_Sum'].sum()
        kpi['risk_orders'] = len(df_filtered[df_filtered['Risk_Sum'] > 0])
        kpi['risk_pct'] = (kpi['risk_orders'] / kpi['orders_count'] * 100) if kpi['orders_count'] > 0 else 0
    else:
        kpi['risk_sum'] = kpi['risk_orders'] = kpi['risk_pct'] = 0

    if 'Data_Completeness' in df_filtered.columns:
        kpi['completeness_avg'] = df_filtered['Data_Completeness'].mean()
    else:
        kpi['completeness_avg'] = 0

    return kpi


def _m(label, value, delta=None, delta_color=None, label_color="#00f5d4"):
    """Одна метрика — HTML, выглядит как st.metric."""
    fs = get_font_sizes()
    v_sz = fs.get('kpi_value', 32)
    l_sz = fs.get('kpi_label', 14)
    
    delta_html = ""
    if delta:
        dc = delta_color or "#888"
        delta_html = f'<div style="font-size:{l_sz}px; color:{dc}; margin-top:2px;">{delta}</div>'
    
    return (
        f'<div style="flex:1; min-width:0;">'
        f'<div style="font-size:{l_sz}px; color:{label_color}; font-weight:700;">{label}</div>'
        f'<div style="font-size:{v_sz}px; color:#ffffff; font-weight:700; line-height:1.3;">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


def render_kpi(df_f, kpi):
    """Отрисовка KPI через st.html() — оригинальный вид, управляемые размеры."""
    fs = get_font_sizes()
    title_sz = fs.get('kpi_title', 28)
    card_sz = fs.get('kpi_label', 14)
    
    vid_count = df_f['Вид'].nunique() if 'Вид' in df_f.columns else 0
    
    dev_pct = kpi['deviation_pct']
    dev_arrow = "↓" if dev_pct < 0 else "↑"
    dev_color = "#10b981" if dev_pct < 0 else "#ff0055"
    
    # Строка 1: Финансы
    row1 = (
        _m("Заказов", fmt(kpi['orders_count'])) +
        _m("План, ₽", fmt(kpi['plan_sum'])) +
        _m("Факт, ₽", fmt(kpi['fact_sum'])) +
        _m("Отклонение, ₽", fmt_sign(kpi['deviation']),
           delta=f"{dev_arrow} {dev_pct:.1f}%", delta_color=dev_color) +
        _m("Средняя стоимость, ₽", fmt(kpi['avg_cost'])) +
        _m("Полнота данных, %", f"{kpi['completeness_avg']:.1f}")
    )
    
    # Строка 2: Иерархия — оригинальные иконки
    row2 = (
        _m("🏢 БЕ", fmt(kpi.get('БЕ_count', 0))) +
        _m("🏭 Заводов", fmt(kpi.get('ЗАВОД_count', 0))) +
        _m("⚙️ Установок", fmt(kpi.get('УСТАНОВКА_count', 0))) +
        _m("📍 Техн. мест", fmt(kpi.get('ТМ_count', 0))) +
        _m("🔧 Ед. оборуд.", fmt(kpi.get('ЕО_count', 0))) +
        _m("📋 Видов заказов", fmt(vid_count))
    )
    
    # Строка 3: Риски
    risk_avg = df_f['Risk_Sum'].mean() if 'Risk_Sum' in df_f.columns else 0
    row3_metrics = (
        _m("Σ Риск-баллов", fmt(kpi['risk_sum'])) +
        _m("С риском (>0)", fmt(kpi['risk_orders']),
           delta=f"↑ + {kpi['risk_pct']:.1f}%", delta_color="#ff0055") +
        _m("Средний риск", f"{risk_avg:.2f}")
    )
    
    # Карточки максимумов — оригинальные цвета и стиль
    cards = ""
    if len(df_f) > 0:
        if 'Fact_N' in df_f.columns:
            idx = df_f['Fact_N'].idxmax()
            oid = str(df_f.loc[idx, 'ID']) if pd.notna(idx) else "—"
            val = df_f['Fact_N'].max()
            cards += (
                f'<div style="flex:1; padding:12px 14px; background:rgba(255,0,85,0.08); '
                f'border-radius:8px; border-left:4px solid #ff0055;">'
                f'<div style="font-size:{card_sz}px; color:#888;">🔴 Макс. факт</div>'
                f'<div style="font-size:{card_sz + 2}px; color:#ff0055; font-weight:bold;">{oid}</div>'
                f'<div style="font-size:{card_sz}px; color:#fff;">{fmt(val)} ₽</div>'
                f'</div>'
            )
        
        if 'Fact_N' in df_f.columns and 'Plan_N' in df_f.columns:
            delta_s = df_f['Fact_N'] - df_f['Plan_N']
            idx = delta_s.idxmax()
            oid = str(df_f.loc[idx, 'ID']) if pd.notna(idx) else "—"
            val = delta_s.max()
            cards += (
                f'<div style="flex:1; padding:12px 14px; background:rgba(255,215,0,0.08); '
                f'border-radius:8px; border-left:4px solid #ffd700;">'
                f'<div style="font-size:{card_sz}px; color:#888;">🟡 Макс. Δ</div>'
                f'<div style="font-size:{card_sz + 2}px; color:#ffd700; font-weight:bold;">{oid}</div>'
                f'<div style="font-size:{card_sz}px; color:#fff;">{fmt_sign(val)} ₽</div>'
                f'</div>'
            )
        
        if 'Risk_Sum' in df_f.columns:
            idx = df_f['Risk_Sum'].idxmax()
            oid = str(df_f.loc[idx, 'ID']) if pd.notna(idx) else "—"
            val = df_f['Risk_Sum'].max()
            cards += (
                f'<div style="flex:1; padding:12px 14px; background:rgba(0,245,212,0.08); '
                f'border-radius:8px; border-left:4px solid #00f5d4;">'
                f'<div style="font-size:{card_sz}px; color:#888;">🟢 Макс. риск</div>'
                f'<div style="font-size:{card_sz + 2}px; color:#00f5d4; font-weight:bold;">{oid}</div>'
                f'<div style="font-size:{card_sz}px; color:#fff;">{int(val)} баллов</div>'
                f'</div>'
            )
    
    html = (
        f'<div style="font-family:Arial,sans-serif; padding:8px 0 16px 0;">'
        f'<div style="font-size:{title_sz}px; color:#ffffff; font-weight:700; margin-bottom:20px;">'
        f'▤ КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ</div>'
        f'<div style="display:flex; gap:8px; margin-bottom:16px;">{row1}</div>'
        f'<div style="display:flex; gap:8px; margin-bottom:16px;">{row2}</div>'
        f'<div style="display:flex; gap:8px; align-items:flex-start;">'
        f'{row3_metrics}'
        f'<div style="display:flex; gap:8px; flex:1;">{cards}</div>'
        f'</div>'
        f'</div>'
    )
    
    st.html(html)
    st.divider()
