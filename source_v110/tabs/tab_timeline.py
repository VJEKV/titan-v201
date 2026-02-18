# -*- coding: utf-8 -*-
"""
tabs/tab_timeline.py — TAB 2: СРОКИ

ИЗМЕНЕНИЯ v111.2:
- Суммы в читаемом формате (435М, 1.2Млрд вместо 435 482 734)
- Убрана диаграмма "Виды работ по месяцам" (перенесена в tab_work_types)
- 3 аналитики: количество, длительность, стоимость
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

from utils.formatters import fmt
from utils.export import create_excel_download
from config.font_config import get_font_sizes, get_big_font, get_hover_style, render_metric_row


MONTH_NAMES = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

MONTH_SHORT = {
    1: 'Янв', 2: 'Фев', 3: 'Мар', 4: 'Апр',
    5: 'Май', 6: 'Июн', 7: 'Июл', 8: 'Авг',
    9: 'Сен', 10: 'Окт', 11: 'Ноя', 12: 'Дек'
}


def _fmt_short(val):
    """Форматирование: всегда 1 знак после запятой."""
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


def _base_layout(height=480, **kwargs):
    """Базовый layout."""
    layout = dict(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=get_big_font(), height=height, hoverlabel=get_hover_style(),
        margin=dict(l=70, r=30, t=40, b=90),
    )
    layout.update(kwargs)
    return layout


def _get_month_data(df_f):
    """Подготовка данных с месяцами."""
    df = df_f.copy()
    for col in ['Начало', 'Конец', 'Факт_Начало']:
        if col in df.columns and df[col].notna().any():
            df['_Месяц'] = df[col].dt.month
            df['_Год'] = df[col].dt.year
            return df, col
    return None, None


def _group_by_month(df_valid, col, agg_func, multi_year):
    """Группировка по месяцам."""
    if multi_year:
        grp = df_valid.groupby(['_Год', '_Месяц'])[col].agg(agg_func).reset_index()
        grp = grp.sort_values(['_Год', '_Месяц'])
        x = grp.apply(
            lambda r: f"{MONTH_SHORT.get(int(r['_Месяц']), '?')} {int(r['_Год'])}", axis=1
        ).values.tolist()
    else:
        grp = df_valid.groupby('_Месяц')[col].agg(agg_func).reset_index()
        grp = grp.sort_values('_Месяц')
        x = [MONTH_NAMES.get(int(m), str(m)) for m in grp['_Месяц']]
    return x, grp[col].tolist()


def render_tab_timeline(df_f):
    """Отрисовка вкладки СРОКИ (v111.2)."""
    
    st.subheader("▣ Анализ сроков")
    st.markdown(
        '<div class="dash-description">📅 <b>Анализ сроков</b> — '
        'помесячная аналитика: количество, длительность, стоимость.</div>',
        unsafe_allow_html=True
    )
    
    df_m, date_col = _get_month_data(df_f)
    if df_m is None:
        st.warning("⚠️ Нет дат для анализа.")
        return
    
    date_options = [c for c in ['Начало', 'Конец', 'Факт_Начало']
                    if c in df_f.columns and df_f[c].notna().any()]
    
    if len(date_options) > 1:
        selected_date_col = st.selectbox(
            "📆 Дата для группировки", options=date_options, index=0,
            key="timeline_date_col"
        )
        df_m['_Месяц'] = df_f[selected_date_col].dt.month
        df_m['_Год'] = df_f[selected_date_col].dt.year
        date_col = selected_date_col
    
    df_valid = df_m[df_m['_Месяц'].notna()].copy()
    if len(df_valid) == 0:
        st.warning("Нет данных с датами.")
        return
    
    years = sorted(df_valid['_Год'].dropna().unique().astype(int))
    multi_year = len(years) > 1
    
    # KPI
    avg_dur = df_valid['Факт_Длит'].mean() if 'Факт_Длит' in df_valid.columns else 0
    avg_cost = df_valid['Fact_N'].mean() if 'Fact_N' in df_valid.columns else 0
    render_metric_row([
        ("ЗАКАЗОВ С ДАТАМИ", fmt(len(df_valid))),
        ("ПЕРИОД", f"{MONTH_SHORT.get(int(df_valid['_Месяц'].min()), '?')} — {MONTH_SHORT.get(int(df_valid['_Месяц'].max()), '?')}"),
        ("СРЕДН. ДЛИТЕЛЬНОСТЬ", f"{avg_dur:.0f} дн." if avg_dur else "—"),
        ("СРЕДН. СТОИМОСТЬ", _fmt_short(avg_cost) + " ₽"),
    ])
    
    st.markdown("---")
    
    # ========================================
    # 1. КОЛИЧЕСТВО ЗАКАЗОВ ПО МЕСЯЦАМ
    # ========================================
    st.markdown("### 📊 1. Распределение заказов по месяцам")
    
    if multi_year:
        grp = df_valid.groupby(['_Год', '_Месяц']).size().reset_index(name='cnt')
        grp = grp.sort_values(['_Год', '_Месяц'])
        x_labels = grp.apply(
            lambda r: f"{MONTH_SHORT.get(int(r['_Месяц']), '?')} {int(r['_Год'])}", axis=1
        ).values.tolist()
        y_vals = grp['cnt'].tolist()
    else:
        grp = df_valid.groupby('_Месяц').size().reset_index(name='cnt')
        grp = grp.sort_values('_Месяц')
        x_labels = [MONTH_NAMES.get(int(m), str(m)) for m in grp['_Месяц']]
        y_vals = grp['cnt'].tolist()
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=x_labels, y=y_vals,
        marker=dict(color='#00f5d4', line=dict(color='#ffffff', width=1)),
        text=y_vals, textposition='outside',
        textfont=dict(color='#00f5d4', size=15),
        hovertemplate="<b>%{x}</b><br>Заказов: %{y}<extra></extra>"
    ))
    fig1.update_layout(**_base_layout(
        xaxis=dict(title="Месяц", tickangle=-45, tickfont=dict(size=get_font_sizes()['plotly_tick'])),
        yaxis=dict(title="Количество заказов", tickfont=dict(size=get_font_sizes()['plotly_tick'])),
    ))
    st.plotly_chart(fig1, use_container_width=True, key="chart_orders_by_month")
    st.markdown('<div style="color:#666; font-size:12px; text-align:right; margin-top:-10px;">📊 Данные: количество заказов (ID), группировка по «' + date_col + '»</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================
    # 2. ДЛИТЕЛЬНОСТЬ ЗАКАЗОВ ПО МЕСЯЦАМ
    # ========================================
    st.markdown("### ⏱ 2. Длительность заказов по месяцам")
    
    has_duration = 'Факт_Длит' in df_valid.columns or 'План_Длит' in df_valid.columns
    
    if has_duration:
        # Средняя длительность (линии)
        dur_traces = []
        if 'План_Длит' in df_valid.columns:
            dur_traces.append(('План_Длит', 'План (средн.)', '#ffd700'))
        if 'Факт_Длит' in df_valid.columns:
            dur_traces.append(('Факт_Длит', 'Факт (средн.)', '#ff0055'))
        
        fig2a = go.Figure()
        for dur_col, label, color in dur_traces:
            x_d, y_d = _group_by_month(df_valid, dur_col, 'mean', multi_year)
            y_d_round = [round(v, 1) if pd.notna(v) else 0 for v in y_d]
            fig2a.add_trace(go.Scatter(
                x=x_d, y=y_d_round, mode='lines+markers+text',
                name=label, line=dict(color=color, width=3), marker=dict(size=10),
                text=[f"{v:.0f}" for v in y_d_round],
                textposition='top center', textfont=dict(size=get_font_sizes()['plotly_text'], color=color),
                hovertemplate=f"<b>{label}</b><br>" + "%{x}<br>%{y:.1f} дн.<extra></extra>"
            ))
        fig2a.update_layout(**_base_layout(
            title=dict(text="Средняя длительность (дни)", font=dict(size=get_font_sizes()['plotly_title'])),
            xaxis=dict(tickangle=-45, tickfont=dict(size=get_font_sizes()['plotly_tick'])),
            yaxis=dict(title="Дни", tickfont=dict(size=get_font_sizes()['plotly_tick'])),
            legend=dict(orientation='h', y=-0.15, font=dict(size=get_font_sizes()['donut_legend'])),
        ))
        st.plotly_chart(fig2a, use_container_width=True, key="chart_avg_duration")
        st.markdown('<div style="color:#666; font-size:12px; text-align:right; margin-top:-10px;">📊 Данные: среднее План_Длит / Факт_Длит (дни)</div>', unsafe_allow_html=True)
        
        # Box plot
        dur_col = 'Факт_Длит' if 'Факт_Длит' in df_valid.columns else 'План_Длит'
        df_box = df_valid[df_valid[dur_col].notna() & (df_valid[dur_col] >= 0)].copy()
        
        if len(df_box) > 0:
            q99 = df_box[dur_col].quantile(0.99)
            df_box_clip = df_box[df_box[dur_col] <= q99].copy()
            
            if multi_year:
                df_box_clip['_Метка'] = df_box_clip.apply(
                    lambda r: f"{MONTH_SHORT.get(int(r['_Месяц']), '?')} {int(r['_Год'])}", axis=1
                )
                df_box_clip = df_box_clip.sort_values(['_Год', '_Месяц'])
            else:
                df_box_clip['_Метка'] = df_box_clip['_Месяц'].map(
                    lambda m: MONTH_NAMES.get(int(m), str(m))
                )
                df_box_clip = df_box_clip.sort_values('_Месяц')
            
            fig2b = go.Figure()
            for label in df_box_clip['_Метка'].unique():
                subset = df_box_clip[df_box_clip['_Метка'] == label]
                fig2b.add_trace(go.Box(
                    y=subset[dur_col], name=label,
                    marker_color='#8b5cf6', boxmean=True
                ))
            fig2b.update_layout(**_base_layout(
                title=dict(text=f"Разброс длительности ({dur_col})", font=dict(size=get_font_sizes()['plotly_title'])),
                yaxis=dict(title="Дни", tickfont=dict(size=get_font_sizes()['plotly_tick'])),
                xaxis=dict(tickfont=dict(size=get_font_sizes()['plotly_tick'])),
                showlegend=False,
            ))
            st.plotly_chart(fig2b, use_container_width=True, key="chart_box_duration")
    else:
        st.info("⚠️ Нет данных о длительности")
    
    st.markdown("---")
    
    # ========================================
    # 3. СРЕДНЯЯ СТОИМОСТЬ ПО МЕСЯЦАМ
    # ========================================
    st.markdown("### 💰 3. Стоимость заказов по месяцам")
    
    if 'Fact_N' in df_valid.columns:
        # Средняя стоимость
        fig3a = go.Figure()
        cost_traces = []
        if 'Plan_N' in df_valid.columns:
            cost_traces.append(('Plan_N', 'План (средн.)', '#ffd700'))
        cost_traces.append(('Fact_N', 'Факт (средн.)', '#ff0055'))
        
        for cost_col, label, color in cost_traces:
            x_c, y_c = _group_by_month(df_valid, cost_col, 'mean', multi_year)
            y_c_clean = [round(v, 0) if pd.notna(v) else 0 for v in y_c]
            fig3a.add_trace(go.Bar(
                x=x_c, y=y_c_clean,
                name=label, marker=dict(color=color, opacity=0.85),
                text=[_fmt_short(v) for v in y_c_clean],
                textposition='outside',
                textfont=dict(size=get_font_sizes()['plotly_text'], color=color),
                hovertemplate=f"<b>{label}</b><br>" + "%{x}<br>" + 
                    "%{text} ₽<extra></extra>"
            ))
        fig3a.update_layout(**_base_layout(
            height=500,
            title=dict(text="Средняя стоимость (₽)", font=dict(size=get_font_sizes()['plotly_title'])),
            xaxis=dict(tickangle=-45, tickfont=dict(size=get_font_sizes()['plotly_tick'])),
            yaxis=dict(title="₽", tickfont=dict(size=get_font_sizes()['plotly_tick']), tickformat=".2s"),
            barmode='group',
            legend=dict(orientation='h', y=-0.15, font=dict(size=get_font_sizes()['donut_legend'])),
        ))
        st.plotly_chart(fig3a, use_container_width=True, key="chart_avg_cost")
        st.markdown('<div style="color:#666; font-size:12px; text-align:right; margin-top:-10px;">📊 Данные: среднее Plan_N / Fact_N (₽)</div>', unsafe_allow_html=True)
    else:
        st.info("⚠️ Нет данных о стоимости")
    
    # Выгрузка
    st.markdown("---")
    if multi_year:
        export_monthly = df_valid.groupby(['_Год', '_Месяц']).agg(Заказов=('ID', 'count')).reset_index()
        export_monthly['Месяц'] = export_monthly['_Месяц'].map(MONTH_NAMES)
        export_monthly.columns = ['Год', 'Месяц_№', 'Заказов', 'Месяц']
    else:
        export_monthly = df_valid.groupby('_Месяц').agg(Заказов=('ID', 'count')).reset_index()
        export_monthly['Месяц'] = export_monthly['_Месяц'].map(MONTH_NAMES)
        export_monthly.columns = ['Месяц_№', 'Заказов', 'Месяц']
    
    excel_timeline = create_excel_download(export_monthly, "timeline_monthly")
    st.download_button(
        "📥 Excel (помесячная сводка)", data=excel_timeline,
        file_name=f"timeline_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_timeline_monthly"
    )
