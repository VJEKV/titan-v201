# -*- coding: utf-8 -*-
"""
tabs/tab_workplaces.py — TAB 5: РАБОЧИЕ МЕСТА v112.3

KPI → Heatmap-таблица (Факт/План/Отклонение/ЕО) → Excel
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from utils.formatters import fmt, fmt_sign
from utils.export import create_excel_download
from config.font_config import get_font_sizes, get_big_font, get_hover_style, render_unified_heatmap, render_metric_row


def _fmt_short(val):
    if pd.isna(val) or val == 0:
        return "0"
    abs_val = abs(val)
    sign = "" if val >= 0 else "-"
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}Млрд"
    elif abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}М"
    elif abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}К"
    else:
        return f"{sign}{abs_val:.1f}"


def _data_source(text):
    st.markdown(
        f'<div style="color:#666; font-size:12px; text-align:right; margin-top:-10px; margin-bottom:10px;">'
        f'📊 Данные: {text}</div>', unsafe_allow_html=True)



def render_tab_workplaces(df_f):
    st.subheader("▣ Аналитика по рабочим местам")
    st.markdown(
        '<div class="dash-description">🏗️ <b>Рабочие места</b> — '
        'кто сколько потратил, перерасход, количество заказов и ЕО.</div>',
        unsafe_allow_html=True)

    if 'РМ' not in df_f.columns:
        st.warning("Поле РМ отсутствует в данных")
        return

    # ==== Агрегация ====
    rm_stats = df_f.groupby('РМ').agg(
        Заказов=('ID', 'count'), Факт=('Fact_N', 'sum'), План=('Plan_N', 'sum')
    ).reset_index()
    if 'ЕО' in df_f.columns:
        eo = df_f.groupby('РМ')['ЕО'].nunique().reset_index()
        eo.columns = ['РМ', 'ЕО_кол']
        rm_stats = rm_stats.merge(eo, on='РМ', how='left')
    else:
        rm_stats['ЕО_кол'] = 0
    rm_stats['Отклонение'] = rm_stats['Факт'] - rm_stats['План']
    rm_stats = rm_stats[rm_stats['РМ'] != 'Н/Д']

    # ==== KPI ====
    overrun_rm = len(rm_stats[rm_stats['Отклонение'] > 0])
    render_metric_row([
        ("РАБОЧИХ МЕСТ", fmt(len(rm_stats))),
        ("ЗАКАЗОВ (Σ)", fmt(rm_stats['Заказов'].sum())),
        ("ФАКТ (Σ)", _fmt_short(rm_stats['Факт'].sum()) + " ₽"),
        ("С ПЕРЕРАСХОДОМ", fmt(overrun_rm) + " РМ"),
    ])

    st.markdown("---")

    # ==== 1. СВОДНАЯ АНАЛИТИКА (НАВЕРХУ) ====
    st.markdown("### 📊 1. Сводная аналитика по рабочим местам")
    
    rm_top = rm_stats.sort_values('Факт', ascending=False).head(10)
    fs = get_font_sizes()
    
    # DONUT
    donut_colors = ['#ff0055', '#ffd700', '#10b981', '#4a9eff', '#8b5cf6',
                    '#ff6b35', '#06b6d4', '#f472b6', '#a78bfa', '#34d399']
    fig_d = go.Figure(go.Pie(
        labels=rm_top['РМ'], values=rm_top['Факт'], hole=0.55,
        marker=dict(colors=donut_colors[:len(rm_top)], line=dict(color='#020408', width=2)),
        textinfo='percent', textposition='outside',
        textfont=dict(size=fs['donut_pct'], color='#fff'),
        hovertemplate="<b>%{label}</b><br>Факт: %{value:,.0f} ₽<br>%{percent}<extra></extra>",
    ))
    fig_d.add_annotation(text=f"<b>{_fmt_short(rm_stats['Факт'].sum())}</b><br><span style='font-size:{fs['donut_legend']}px'>₽ Факт</span>",
                         x=0.5, y=0.5, font=dict(size=fs['donut_center'], color='#FFF'), showarrow=False)
    fig_d.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=get_big_font(), height=600,
                        showlegend=True, legend=dict(font=dict(size=fs['donut_legend'], color='#ccc'), orientation='h', y=-0.1),
                        margin=dict(l=30, r=30, t=30, b=60), hoverlabel=get_hover_style())
    st.plotly_chart(fig_d, use_container_width=True, key="chart_rm_donut")

    # BARS
    rm_bars = rm_stats.sort_values('Заказов', ascending=False).head(15)
    fig_b = go.Figure(go.Bar(
        y=rm_bars['РМ'], x=rm_bars['Заказов'], orientation='h',
        marker=dict(color='#4a9eff'),
        text=[f"{int(z)} зак. • {_fmt_short(f)} ₽" for z, f in zip(rm_bars['Заказов'], rm_bars['Факт'])],
        textposition='outside', textfont=dict(size=fs['bar_label'], color='#ccc'),
    ))
    fig_b.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                        font=get_big_font(), height=max(500, len(rm_bars)*45+100),
                        yaxis=dict(categoryorder='total ascending', tickfont=dict(size=fs['plotly_tick'])),
                        xaxis=dict(title="Заказов", tickfont=dict(size=fs['plotly_tick'])),
                        margin=dict(l=350, r=80, t=30, b=50), hoverlabel=get_hover_style())
    st.plotly_chart(fig_b, use_container_width=True, key="chart_rm_bars")

    _data_source(f"{len(rm_stats)} рабочих мест, {rm_stats['Заказов'].sum()} заказов, {_fmt_short(rm_stats['Факт'].sum())} ₽ факт")
    st.markdown("---")

    # ==== 2. Перерасход — TOP-15 ====
    st.markdown("### 🔴 2. РМ с перерасходом (TOP-15)")
    rm_over = rm_stats[rm_stats['Отклонение'] > 0].sort_values('Отклонение', ascending=False).head(15)
    if len(rm_over) > 0:
        render_unified_heatmap(rm_over, 'РМ', 'rm_over', extra_cols=[('ЕО_кол', 'ЕО', 'center')] if 'ЕО_кол' in rm_over.columns else None)
    else:
        st.success("✓ Нет РМ с перерасходом")

    st.markdown("---")

    # ==== 3. Экономия — TOP-15 ====
    st.markdown("### 🟢 3. РМ с экономией (TOP-15)")
    rm_save = rm_stats[rm_stats['Отклонение'] < 0].sort_values('Отклонение').head(15)
    if len(rm_save) > 0:
        render_unified_heatmap(rm_save, 'РМ', 'rm_save', extra_cols=[('ЕО_кол', 'ЕО', 'center')] if 'ЕО_кол' in rm_save.columns else None)
    else:
        st.info("Нет РМ с экономией")

    _data_source("Отклонение = Fact_N − Plan_N, группировка по РМ")

    st.markdown("---")

    # ==== Сводная таблица + Excel ====
    with st.expander(f"📋 Все рабочие места ({len(rm_stats)})", expanded=False):
        tbl = rm_stats.sort_values('Отклонение', ascending=False).copy()
        tbl['План'] = tbl['План'].apply(lambda x: f"{fmt(x)} ₽")
        tbl['Факт'] = tbl['Факт'].apply(lambda x: f"{fmt(x)} ₽")
        tbl['Отклонение'] = tbl['Отклонение'].apply(fmt_sign)
        st.dataframe(tbl, use_container_width=True, hide_index=True, height=400)
        excel = create_excel_download(rm_stats, "workplaces")
        st.download_button("📥 Excel (рабочие места)", data=excel,
                           file_name=f"workplaces_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_rm")
