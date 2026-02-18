# -*- coding: utf-8 -*-
"""
tabs/tab_work_types.py — TAB 3: ВИДЫ РАБОТ

ИЗМЕНЕНИЯ v111.2:
- ДОБАВЛЕНО: Виды работ по месяцам (stacked bar, перенесено из СРОКИ)
- ДОБАВЛЕНО: Стоимость по видам работ (горизонтальный bar)
- Короткие подписи сумм (_fmt_short)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.constants import ВНЕПЛАНОВЫЕ_ВИДЫ
from utils.formatters import fmt, fmt_sign
from utils.export import create_excel_download
from config.font_config import get_font_sizes, get_big_font, get_hover_style, render_unified_heatmap, render_metric_row


MONTH_SHORT = {
    1: 'Янв', 2: 'Фев', 3: 'Мар', 4: 'Апр',
    5: 'Май', 6: 'Июн', 7: 'Июл', 8: 'Авг',
    9: 'Сен', 10: 'Окт', 11: 'Ноя', 12: 'Дек'
}
MONTH_NAMES = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
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
    layout = dict(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=get_big_font(), height=height, hoverlabel=get_hover_style(),
        margin=dict(l=70, r=30, t=40, b=90),
    )
    layout.update(kwargs)
    return layout


def _data_source(text):
    st.markdown(
        f'<div style="color:#666; font-size:12px; text-align:right; margin-top:-10px; margin-bottom:10px;">'
        f'📊 Данные: {text}</div>', unsafe_allow_html=True)



def render_tab_work_types(df_f):
    """Отрисовка вкладки ВИДЫ РАБОТ (v112.3)."""
    
    st.subheader("▣ Анализ по видам работ")
    st.markdown(
        '<div class="dash-description">🔧 <b>Виды работ</b> — '
        'кто сколько потратил, перерасход, плановые vs внеплановые, помесячная динамика.</div>',
        unsafe_allow_html=True
    )
    
    # Статистика по видам
    vid_stats = df_f.groupby('Вид').agg(
        Заказов=('ID', 'count'), Факт=('Fact_N', 'sum'), План=('Plan_N', 'sum')
    ).reset_index()
    vid_stats['Отклонение'] = vid_stats['Факт'] - vid_stats['План']
    
    if 'Вид_Код' in df_f.columns:
        vid_codes = df_f.groupby('Вид')['Вид_Код'].first().to_dict()
        vid_stats['Внеплан'] = vid_stats['Вид'].map(vid_codes).isin(ВНЕПЛАНОВЫЕ_ВИДЫ)
    else:
        vid_stats['Внеплан'] = False
    
    # KPI
    planned = vid_stats[~vid_stats['Внеплан']]
    unplanned = vid_stats[vid_stats['Внеплан']]
    total_orders = vid_stats['Заказов'].sum()
    
    unpl_pct = unplanned['Заказов'].sum() / max(total_orders, 1) * 100
    total_dev = vid_stats['Отклонение'].sum()
    render_metric_row([
        ("ВИДОВ РАБОТ", fmt(len(vid_stats))),
        ("ЗАКАЗОВ (Σ)", fmt(total_orders)),
        ("ВНЕПЛАНОВЫЕ", fmt(unplanned['Заказов'].sum()) + " зак.", f"{unpl_pct:.1f}%", "#ff6b6b"),
        ("ОТКЛОНЕНИЕ (Σ)", _fmt_short(total_dev) + " ₽"),
    ])
    
    st.markdown("---")
    
    # ========================================
    # 1. HEATMAP ТАБЛИЦА — ВСЕ ВИДЫ РАБОТ
    # ========================================
    st.markdown("### 📋 1. Виды работ: План, Факт, Отклонение")
    
    vid_sorted = vid_stats.sort_values('Отклонение', ascending=False)
    render_unified_heatmap(vid_sorted, 'Вид', 'vr')
    _data_source("Отклонение = Fact_N − Plan_N, группировка по Вид")
    
    st.markdown("---")
    
    # ========================================
    # 2. СВОДНАЯ АНАЛИТИКА: DONUT + СТОЛБЦЫ
    # ========================================
    st.markdown("### 📊 2. Сводная аналитика по видам работ")
    
    vid_top = vid_stats.sort_values('Факт', ascending=False).copy()
    
    col_donut, col_bars = st.columns([2, 3])
    
    with col_donut:
        # Donut: распределение факт.затрат по видам
        donut_colors = ['#ff0055', '#ffd700', '#10b981', '#4a9eff', '#8b5cf6',
                        '#ff6b35', '#06b6d4', '#f472b6', '#a78bfa', '#34d399']
        
        fig_donut = go.Figure(go.Pie(
            labels=vid_top['Вид'],
            values=vid_top['Факт'],
            hole=0.55,
            marker=dict(colors=donut_colors[:len(vid_top)], line=dict(color='#020408', width=2)),
            textinfo='percent',
            textposition='outside',
            textfont=dict(size=get_font_sizes()['donut_pct'], color='#ffffff'),
            hovertemplate="<b>%{label}</b><br>Факт: %{value:,.0f} ₽<br>Доля: %{percent}<extra></extra>",
        ))
        total_fact_vr = vid_top['Факт'].sum()
        fig_donut.add_annotation(
            text=f"<b>{_fmt_short(total_fact_vr)}</b><br><span style='font-size:14px'>₽ Факт</span>",
            x=0.5, y=0.5, font=dict(size=get_font_sizes()['donut_center'], color='#FFFFFF'), showarrow=False
        )
        fig_donut.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', font=get_big_font(), height=480,
            showlegend=True,
            legend=dict(font=dict(size=get_font_sizes()['donut_legend'], color='#ccc'), orientation='h', y=-0.1),
            margin=dict(l=30, r=30, t=30, b=60),
            hoverlabel=get_hover_style(),
        )
        st.plotly_chart(fig_donut, use_container_width=True, key="chart_vr_donut")
    
    with col_bars:
        # Горизонтальные столбцы: заказы по видам
        vid_bars = vid_top.sort_values('Заказов', ascending=True)
        bar_h = max(350, len(vid_bars) * 40 + 80)
        
        fig_bars = go.Figure(go.Bar(
            y=vid_bars['Вид'].str[:45],
            x=vid_bars['Заказов'],
            orientation='h',
            marker=dict(color='#4a9eff', line=dict(color='#ffffff', width=1)),
            text=[f"{int(v)} зак. • {_fmt_short(f)} ₽" for v, f in zip(vid_bars['Заказов'], vid_bars['Факт'])],
            textposition='outside',
            textfont=dict(size=get_font_sizes()['bar_label'], color='#ccc'),
            hovertemplate="<b>%{y}</b><br>Заказов: %{x}<extra></extra>"
        ))
        fig_bars.update_layout(**_base_layout(
            height=bar_h,
            xaxis=dict(title="Количество заказов", tickfont=dict(size=get_font_sizes()['plotly_tick'])),
            yaxis=dict(tickfont=dict(size=get_font_sizes()['plotly_tick']), categoryorder='total ascending'),
            margin=dict(l=280, r=120, t=30, b=40),
        ))
        st.plotly_chart(fig_bars, use_container_width=True, key="chart_vr_bars")
    
    _data_source(f"{len(vid_stats)} видов работ, {fmt(total_orders)} заказов, {_fmt_short(total_fact_vr)} ₽ факт")
    
    st.markdown("---")
    
    # ========================================
    # ВИДЫ РАБОТ ПО МЕСЯЦАМ (перенесено из СРОКИ)
    # ========================================
    st.markdown("### 📅 3. Виды работ по месяцам")
    
    # Определяем колонку с датой
    date_col = None
    for col in ['Начало', 'Конец', 'Факт_Начало']:
        if col in df_f.columns and df_f[col].notna().any():
            date_col = col
            break
    
    if date_col and 'Вид' in df_f.columns:
        df_m = df_f.copy()
        df_m['_Месяц'] = df_f[date_col].dt.month
        df_m['_Год'] = df_f[date_col].dt.year
        df_valid = df_m[df_m['_Месяц'].notna()].copy()
        
        years = sorted(df_valid['_Год'].dropna().unique().astype(int))
        multi_year = len(years) > 1
        
        vid_counts = df_valid['Вид'].value_counts()
        top_vids = vid_counts.head(8).index.tolist()
        
        colors_palette = ['#00f5d4', '#ff0055', '#ffd700', '#8b5cf6',
                          '#ff6b35', '#10b981', '#06b6d4', '#f472b6']
        
        fig4 = go.Figure()
        
        for i, vid in enumerate(top_vids):
            df_vid = df_valid[df_valid['Вид'] == vid]
            
            if multi_year:
                grp = df_vid.groupby(['_Год', '_Месяц']).size().reset_index(name='cnt')
                grp = grp.sort_values(['_Год', '_Месяц'])
                x_v = grp.apply(
                    lambda r: f"{MONTH_SHORT.get(int(r['_Месяц']), '?')} {int(r['_Год'])}", axis=1
                ).values.tolist()
            else:
                grp = df_vid.groupby('_Месяц').size().reset_index(name='cnt')
                grp = grp.sort_values('_Месяц')
                x_v = [MONTH_NAMES.get(int(m), str(m)) for m in grp['_Месяц']]
            
            vid_short = vid[:45] + '…' if len(vid) > 45 else vid
            
            fig4.add_trace(go.Bar(
                x=x_v, y=grp['cnt'].tolist(),
                name=vid_short,
                marker=dict(color=colors_palette[i % len(colors_palette)]),
                hovertemplate=f"<b>{vid_short}</b><br>" + "%{x}: %{y} заказов<extra></extra>"
            ))
        
        fig4.update_layout(**_base_layout(
            height=550,
            barmode='stack',
            xaxis=dict(title="Месяц", tickangle=-45, tickfont=dict(size=get_font_sizes()['plotly_tick'])),
            yaxis=dict(title="Количество заказов", tickfont=dict(size=get_font_sizes()['plotly_tick'])),
            legend=dict(orientation='h', y=-0.2, font=dict(size=get_font_sizes()['donut_legend'])),
            margin=dict(l=70, r=30, t=40, b=130),
        ))
        st.plotly_chart(fig4, use_container_width=True, key="chart_vid_by_month")
        
        # Сводная таблица
        with st.expander("📋 Сводная таблица: виды работ × месяцы", expanded=False):
            df_valid_copy = df_valid.copy()
            if multi_year:
                df_valid_copy['_Метка'] = df_valid_copy.apply(
                    lambda r: f"{MONTH_SHORT.get(int(r['_Месяц']), '?')} {int(r['_Год'])}", axis=1
                )
            else:
                df_valid_copy['_Метка'] = df_valid_copy['_Месяц'].map(
                    lambda m: MONTH_NAMES.get(int(m), str(m))
                )
            pivot = pd.crosstab(df_valid_copy['Вид'], df_valid_copy['_Метка'])
            pivot['ИТОГО'] = pivot.sum(axis=1)
            pivot = pivot.sort_values('ИТОГО', ascending=False)
            st.dataframe(pivot, use_container_width=True, height=350)
    else:
        st.info("⚠️ Нет дат для помесячного анализа видов работ")
    
    st.markdown("---")
    
    # ========================================
    # ВНЕПЛАНОВЫЕ РАБОТЫ
    # ========================================
    st.markdown("### ⚠️ Детализация внеплановых работ (LK02, LK04, LK05)")
    
    if 'Вид_Код' in df_f.columns:
        unplanned_orders = df_f[df_f['Вид_Код'].isin(ВНЕПЛАНОВЫЕ_ВИДЫ)]
    else:
        unplanned_orders = df_f[df_f['Вид'].str.contains('LK02|LK04|LK05', na=False)]
    
    if len(unplanned_orders) > 0:
        cols_to_show = ['ID', 'Вид_Код', 'Вид', 'ТМ', 'Plan_N', 'Fact_N']
        cols_exist = [c for c in cols_to_show if c in unplanned_orders.columns]
        
        unpl_table = unplanned_orders[cols_exist].copy()
        unpl_table = unpl_table.sort_values('Fact_N', ascending=False).head(100)
        
        col_names = {'ID': 'Заказ', 'Вид_Код': 'Код', 'Вид': 'Вид работ',
                     'ТМ': 'ТМ', 'Plan_N': 'План', 'Fact_N': 'Факт'}
        unpl_table.columns = [col_names.get(c, c) for c in cols_exist]
        
        if 'План' in unpl_table.columns:
            unpl_table['План'] = unpl_table['План'].apply(fmt)
        if 'Факт' in unpl_table.columns:
            unpl_table['Факт'] = unpl_table['Факт'].apply(fmt)
        
        st.dataframe(unpl_table, use_container_width=True, hide_index=True, height=350)
        
        export_cols = ['ID', 'Вид_Код', 'Вид', 'ТМ', 'Plan_N', 'Fact_N']
        export_exist = [c for c in export_cols if c in unplanned_orders.columns]
        
        excel_unpl = create_excel_download(unplanned_orders[export_exist], "unplanned")
        st.download_button("📥 Excel (внеплановые)", data=excel_unpl,
                           file_name=f"unplanned_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_unpl")
    else:
        st.success("✓ Нет внеплановых работ")
