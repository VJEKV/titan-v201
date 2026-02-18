# -*- coding: utf-8 -*-
"""
tabs/tab_finance.py — TAB 1: ФИНАНСЫ

v112.1:
- Суммарная стоимость по месяцам — НАВЕРХУ
- Вертикальные столбчатые диаграммы для Цехов и ТМ
- Большой Donut ABC (x3) + плашки с информацией
- Подписи источника данных на каждой диаграмме
- Сворачиваемые таблицы
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from utils.formatters import fmt, fmt_sign
from utils.export import create_excel_download
from config.font_config import get_font_sizes, get_big_font, get_hover_style, render_metric_row


MONTH_SHORT = {
    1: 'Янв', 2: 'Фев', 3: 'Мар', 4: 'Апр',
    5: 'Май', 6: 'Июн', 7: 'Июл', 8: 'Авг',
    9: 'Сен', 10: 'Окт', 11: 'Ноя', 12: 'Дек'
}


def _fmt_short(val):
    """Форматирование: 101.0М, 4.1М, 1.2Млрд, 371.0К — всегда 1 знак после запятой."""
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
        margin=dict(l=70, r=30, t=60, b=90),
    )
    layout.update(kwargs)
    return layout


def _data_source(text):
    """Подпись источника данных."""
    st.markdown(
        f'<div style="color:#666; font-size:12px; text-align:right; margin-top:-10px; margin-bottom:10px;">'
        f'📊 Данные: {text}</div>',
        unsafe_allow_html=True
    )


def _render_heatmap_table(df_data, name_col, mode, prefix):
    """
    Heatmap-таблица через st.html. 
    mode: 'overrun', 'savings', 'unified' (красный→зелёный)
    """
    if len(df_data) == 0:
        return
    
    fs = get_font_sizes()
    abs_max = df_data['Отклонение'].abs().max()
    if abs_max == 0:
        abs_max = 1
    
    rows_html = []
    for i, (_, row) in enumerate(df_data.iterrows()):
        val = row['Отклонение']
        intensity = min(abs(val) / abs_max, 1.0)
        
        if mode == 'unified':
            if val >= 0:
                r = int(40 + intensity * 180)
                g = int(10)
                b = int(20 + intensity * 30)
                text_color = '#ff6b6b' if intensity > 0.2 else '#ff9999'
                sign = "+"
            else:
                r = int(10)
                g = int(40 + intensity * 140)
                b = int(30 + intensity * 80)
                text_color = '#6bffb8' if intensity > 0.2 else '#99ffcc'
                sign = ""
        elif mode == 'overrun':
            r = int(40 + intensity * 180)
            g, b = 10, int(20 + intensity * 30)
            text_color = '#ff6b6b' if intensity > 0.3 else '#ff9999'
            sign = "+"
        else:
            r = 10
            g = int(40 + intensity * 140)
            b = int(30 + intensity * 80)
            text_color = '#6bffb8' if intensity > 0.3 else '#99ffcc'
            sign = ""
        
        bg_color = f"rgb({r},{g},{b})"
        name = str(row[name_col])
        
        rows_html.append(
            f'<tr style="background:{bg_color}; border-bottom:1px solid #333;">'
            f'<td style="padding:10px 14px; font-size:{fs["table_name"]}px; color:#fff; max-width:400px; '
            f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" '
            f'title="{name}">{i+1}. {name}</td>'
            f'<td style="padding:10px 14px; font-size:{fs["table_value"]}px; color:#e0e0e0; text-align:right;">'
            f'{_fmt_short(row["План"])} ₽</td>'
            f'<td style="padding:10px 14px; font-size:{fs["table_value"]}px; color:#e0e0e0; text-align:right;">'
            f'{_fmt_short(row["Факт"])} ₽</td>'
            f'<td style="padding:10px 14px; font-size:{fs["table_deviation"]}px; font-weight:bold; color:{text_color}; text-align:right;">'
            f'{sign}{_fmt_short(val)} ₽</td>'
            f'<td style="padding:10px 14px; font-size:{fs["table_value"] - 1}px; color:#ccc; text-align:center;">'
            f'{int(row["Заказов"])}</td>'
            f'</tr>'
        )
    
    html = (
        '<div style="overflow-x:auto; border-radius:8px; border:1px solid #333; margin:8px 0;">'
        '<table style="width:100%; border-collapse:collapse; font-family:Arial,sans-serif;">'
        f'<thead><tr style="background:#0a0a1a; border-bottom:2px solid #444;">'
        f'<th style="padding:10px 14px; color:#aaa; text-align:left; font-size:{fs["table_header"]}px;">Наименование</th>'
        f'<th style="padding:10px 14px; color:#aaa; text-align:right; font-size:{fs["table_header"]}px;">План</th>'
        f'<th style="padding:10px 14px; color:#aaa; text-align:right; font-size:{fs["table_header"]}px;">Факт</th>'
        f'<th style="padding:10px 14px; color:#aaa; text-align:right; font-size:{fs["table_header"]}px;">Отклонение</th>'
        f'<th style="padding:10px 14px; color:#aaa; text-align:center; font-size:{fs["table_header"]}px;">Заказов</th>'
        '</tr></thead><tbody>'
        + ''.join(rows_html)
        + '</tbody></table></div>'
    )
    st.html(html)


def render_tab_finance(df_f):
    """Отрисовка вкладки ФИНАНСЫ (v112.1)."""
    
    st.subheader("▣ Финансовый анализ")
    st.markdown(
        '<div class="dash-description">💰 <b>Финансовый анализ</b> — '
        'суммарная стоимость, отклонения по Цехам и ТМ, распределение по ABC.</div>',
        unsafe_allow_html=True
    )
    
    # KPI
    total_plan = df_f['Plan_N'].sum() if 'Plan_N' in df_f.columns else 0
    total_fact = df_f['Fact_N'].sum() if 'Fact_N' in df_f.columns else 0
    total_dev = total_fact - total_plan
    dev_pct = (total_dev / total_plan * 100) if total_plan != 0 else 0
    
    overrun_count = len(df_f[df_f['Fact_N'] > df_f['Plan_N']]) if 'Plan_N' in df_f.columns else 0
    dev_color = "#ff0055" if total_dev > 0 else "#10b981"
    render_metric_row([
        ("ПЛАН (Σ)", _fmt_short(total_plan) + " ₽"),
        ("ФАКТ (Σ)", _fmt_short(total_fact) + " ₽"),
        ("ОТКЛОНЕНИЕ", _fmt_short(total_dev) + " ₽", f"{dev_pct:+.1f}%", dev_color),
        ("С ПЕРЕРАСХОДОМ", fmt(overrun_count) + " зак."),
    ])
    
    st.markdown("---")
    
    # ========================================
    # 1. СУММАРНАЯ СТОИМОСТЬ ПО МЕСЯЦАМ
    # ========================================
    st.markdown("### 📅 1. Суммарная фактическая стоимость по месяцам")
    
    date_col = None
    for col in ['Начало', 'Конец', 'Факт_Начало']:
        if col in df_f.columns and df_f[col].notna().any():
            date_col = col
            break
    
    if date_col and 'Fact_N' in df_f.columns:
        # Только заказы с фактической стоимостью > 0
        df_m = df_f[df_f['Fact_N'] > 0].copy()
        df_m['_Месяц'] = df_m[date_col].dt.month
        df_m['_Год'] = df_m[date_col].dt.year
        df_valid = df_m[df_m['_Месяц'].notna()].copy()
        
        if len(df_valid) > 0:
            years = sorted(df_valid['_Год'].dropna().unique().astype(int))
            multi_year = len(years) > 1
            
            if multi_year:
                grp = df_valid.groupby(['_Год', '_Месяц'])['Fact_N'].sum().reset_index()
                grp = grp.sort_values(['_Год', '_Месяц'])
                x_labels = grp.apply(
                    lambda r: f"{MONTH_SHORT.get(int(r['_Месяц']), '?')} {int(r['_Год'])}", axis=1
                ).values.tolist()
            else:
                grp = df_valid.groupby('_Месяц')['Fact_N'].sum().reset_index()
                grp = grp.sort_values('_Месяц')
                x_labels = [MONTH_SHORT.get(int(m), str(m)) for m in grp['_Месяц']]
            
            y_vals = [round(v, 0) if pd.notna(v) else 0 for v in grp['Fact_N'].tolist()]
            
            # Отрезаем нулевой хвост
            while y_vals and y_vals[-1] == 0:
                y_vals.pop()
                x_labels.pop()
            
            fig_sum = go.Figure()
            fig_sum.add_trace(go.Bar(
                x=x_labels, y=y_vals,
                marker=dict(color='#10b981', line=dict(color='#ffffff', width=1)),
                text=[_fmt_short(v) for v in y_vals],
                textposition='outside',
                textfont=dict(size=get_font_sizes()['plotly_text'], color='#10b981'),
                hovertemplate="<b>%{x}</b><br>Σ Факт: %{text} ₽<extra></extra>"
            ))
            fig_sum.update_layout(**_base_layout(
                height=480,
                title=dict(text="Суммарная фактическая стоимость (₽)", font=dict(size=get_font_sizes()['plotly_title'])),
                xaxis=dict(tickangle=-45, tickfont=dict(size=get_font_sizes()['plotly_tick'])),
                yaxis=dict(title="₽", tickfont=dict(size=get_font_sizes()['plotly_tick']), tickformat=".2s"),
            ))
            st.plotly_chart(fig_sum, use_container_width=True, key="chart_sum_cost_finance")
            _data_source(f"Fact_N (факт. стоимость > 0), группировка по «{date_col}»")
    else:
        st.info("⚠️ Нет дат для помесячного анализа")
    
    st.markdown("---")
    
    # ========================================
    # 2. ЦЕХА — HEATMAP ТАБЛИЦА
    # ========================================
    st.markdown("### 🏭 2. Отклонения по ЦЕХАМ (Факт − План)")
    
    if 'ЦЕХ' in df_f.columns:
        ceh_stats = df_f.groupby('ЦЕХ').agg(
            Заказов=('ID', 'count'), Факт=('Fact_N', 'sum'), План=('Plan_N', 'sum')
        ).reset_index()
        if 'ЕО' in df_f.columns:
            ceh_eo = df_f.groupby('ЦЕХ')['ЕО'].nunique().reset_index()
            ceh_eo.columns = ['ЦЕХ', 'ЕО_кол']
            ceh_stats = ceh_stats.merge(ceh_eo, on='ЦЕХ', how='left')
        else:
            ceh_stats['ЕО_кол'] = 0
        ceh_stats['Отклонение'] = ceh_stats['Факт'] - ceh_stats['План']
        ceh_stats = ceh_stats[ceh_stats['ЦЕХ'] != 'Н/Д']
        
        # Единая heatmap — все цеха, от перерасхода к экономии
        ceh_all = ceh_stats.sort_values('Отклонение', ascending=False)
        _render_heatmap_table(ceh_all, 'ЦЕХ', 'unified', 'ceh')
        
        _data_source("Отклонение = Fact_N − Plan_N, группировка по ЦЕХ")
        
        with st.expander(f"📋 Таблица всех цехов ({len(ceh_stats)})", expanded=False):
            tbl_ceh = ceh_stats.sort_values('Отклонение', ascending=False).copy()
            tbl_ceh['План'] = tbl_ceh['План'].apply(lambda x: f"{fmt(x)} ₽")
            tbl_ceh['Факт'] = tbl_ceh['Факт'].apply(lambda x: f"{fmt(x)} ₽")
            tbl_ceh['Отклонение'] = tbl_ceh['Отклонение'].apply(fmt_sign)
            st.dataframe(tbl_ceh, use_container_width=True, hide_index=True, height=400)
            excel_ceh = create_excel_download(ceh_stats, "ceha")
            st.download_button("📥 Excel (цеха)", data=excel_ceh,
                               file_name=f"ceha_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="dl_ceh")
    else:
        st.warning("Поле ЦЕХ отсутствует")
    
    st.markdown("---")
    
    # ========================================
    # 3. ТМ — HEATMAP ТАБЛИЦА
    # ========================================
    st.markdown("### 📍 3. Отклонения по ТМ (Факт − План)")
    st.markdown('<div class="analytics-hint">📊 Только реальные ТМ (код ≥ 12 символов).</div>', unsafe_allow_html=True)
    
    if 'ТМ_Код' in df_f.columns:
        df_tm = df_f[df_f['ТМ_Код'].astype(str).str.len() >= 12].copy()
    else:
        df_tm = df_f[df_f['ТМ'].astype(str).str.match(r'^ST\d{2}\.\d{4}\.\w+', na=False)].copy()
    
    if len(df_tm) > 0:
        tm_stats = df_tm.groupby('ТМ').agg(
            Заказов=('ID', 'count'), Факт=('Fact_N', 'sum'), План=('Plan_N', 'sum')
        ).reset_index()
        if 'ЕО' in df_tm.columns:
            tm_eo = df_tm.groupby('ТМ')['ЕО'].nunique().reset_index()
            tm_eo.columns = ['ТМ', 'ЕО_кол']
            tm_stats = tm_stats.merge(tm_eo, on='ТМ', how='left')
        else:
            tm_stats['ЕО_кол'] = 0
        tm_stats['Отклонение'] = tm_stats['Факт'] - tm_stats['План']
        
        tm_over = tm_stats[tm_stats['Отклонение'] > 0].sort_values('Отклонение', ascending=False).head(15)
        tm_save = tm_stats[tm_stats['Отклонение'] < 0].sort_values('Отклонение').head(15)
        tm_combined = pd.concat([tm_over, tm_save]).sort_values('Отклонение', ascending=False)
        
        _render_heatmap_table(tm_combined, 'ТМ', 'unified', 'tm')
        
        _data_source("Отклонение = Fact_N − Plan_N, TOP-15 перерасход + TOP-15 экономия по ТМ")
        
        # Сворачиваемые таблицы
        all_overrun = tm_stats[tm_stats['Отклонение'] > 0].sort_values('Отклонение', ascending=False)
        all_savings = tm_stats[tm_stats['Отклонение'] < 0].copy()
        all_savings['Экономия_abs'] = all_savings['Отклонение'].abs()
        all_savings = all_savings.sort_values('Экономия_abs', ascending=False)
        
        if len(all_overrun) > 0:
            with st.expander(f"📋 Все ТМ с перерасходом ({len(all_overrun)})", expanded=False):
                tbl_o = all_overrun.copy()
                tbl_o['План'] = tbl_o['План'].apply(lambda x: f"{fmt(x)} ₽")
                tbl_o['Факт'] = tbl_o['Факт'].apply(lambda x: f"{fmt(x)} ₽")
                tbl_o['Отклонение'] = tbl_o['Отклонение'].apply(lambda x: f"+{fmt(x)} ₽")
                st.dataframe(tbl_o[['ТМ', 'Заказов', 'ЕО_кол', 'План', 'Факт', 'Отклонение']],
                             use_container_width=True, hide_index=True, height=400)
                @st.fragment
                def download_overrun():
                    excel_o = create_excel_download(all_overrun, "overrun")
                    st.download_button("📥 Excel (перерасход)", data=excel_o,
                                       file_name=f"overrun_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       key="dl_overrun")
                download_overrun()
        
        if len(all_savings) > 0:
            with st.expander(f"📋 Все ТМ с экономией ({len(all_savings)})", expanded=False):
                tbl_s = all_savings.copy()
                tbl_s['План'] = tbl_s['План'].apply(lambda x: f"{fmt(x)} ₽")
                tbl_s['Факт'] = tbl_s['Факт'].apply(lambda x: f"{fmt(x)} ₽")
                tbl_s['Отклонение'] = tbl_s['Отклонение'].apply(lambda x: f"{fmt(x)} ₽")
                st.dataframe(tbl_s[['ТМ', 'Заказов', 'ЕО_кол', 'План', 'Факт', 'Отклонение']],
                             use_container_width=True, hide_index=True, height=400)
                @st.fragment
                def download_savings():
                    excel_s = create_excel_download(
                        all_savings[['ТМ', 'Заказов', 'ЕО_кол', 'План', 'Факт', 'Отклонение']], "savings"
                    )
                    st.download_button("📥 Excel (экономия)", data=excel_s,
                                       file_name=f"savings_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       key="dl_savings")
                download_savings()
    else:
        st.warning("Нет данных с реальными ТМ")
    
    st.markdown("---")
    
    # ========================================
    # 4. ABC — БОЛЬШОЙ DONUT + ПЛАШКИ
    # ========================================
    st.markdown("### 📦 4. Распределение по ABC")
    
    abc_data = df_f.groupby('ABC').agg(Заказов=('ID', 'count'), Сумма=('Fact_N', 'sum')).reset_index()
    if 'ЕО' in df_f.columns:
        abc_eo = df_f.groupby('ABC')['ЕО'].nunique().reset_index()
        abc_eo.columns = ['ABC', 'ЕО_кол']
        abc_data = abc_data.merge(abc_eo, on='ABC', how='left')
    else:
        abc_data['ЕО_кол'] = 0
    
    abc_total = abc_data['Сумма'].sum()
    abc_data['Процент'] = (abc_data['Сумма'] / max(abc_total, 1) * 100).round(1)
    
    abc_cm = {
        # Короткие
        'A': '#ff0055', 'B': '#ffd700', 'C': '#00f5d4',
        # Полные названия
        'Высококритичное': '#ff0055',
        'Оч.высокая/Особокрит': '#ff3366',
        'Средней критичности': '#ffd700',
        'Низкой критичности': '#10b981',
        'Не критично': '#06b6d4',
        'Н/Д': '#555555',
    }
    # Динамическая палитра для неизвестных значений
    _fallback_colors = ['#8b5cf6', '#ff6b35', '#f472b6', '#34d399', '#60a5fa', '#a78bfa']
    _used = 0
    for _, r in abc_data.iterrows():
        if r['ABC'] not in abc_cm:
            abc_cm[r['ABC']] = _fallback_colors[_used % len(_fallback_colors)]
            _used += 1
    
    abc_colors = [abc_cm.get(r['ABC'], '#888') for _, r in abc_data.iterrows()]
    
    # Фоны плашек — тёмные оттенки тех же цветов
    abc_bg_map = {
        '#ff0055': 'linear-gradient(135deg, #3d0018 0%, #1a0a14 100%)',
        '#ff3366': 'linear-gradient(135deg, #3d0020 0%, #1a0a14 100%)',
        '#ffd700': 'linear-gradient(135deg, #3d3000 0%, #1a1a0a 100%)',
        '#10b981': 'linear-gradient(135deg, #003d2e 0%, #0a1a16 100%)',
        '#06b6d4': 'linear-gradient(135deg, #003040 0%, #0a1520 100%)',
        '#555555': 'linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%)',
        '#8b5cf6': 'linear-gradient(135deg, #2a1a4d 0%, #150d28 100%)',
        '#ff6b35': 'linear-gradient(135deg, #3d1a00 0%, #1a0d00 100%)',
        '#f472b6': 'linear-gradient(135deg, #3d1a2e 0%, #1a0d16 100%)',
        '#34d399': 'linear-gradient(135deg, #0a3d2e 0%, #051a16 100%)',
        '#60a5fa': 'linear-gradient(135deg, #0a2040 0%, #051020 100%)',
        '#a78bfa': 'linear-gradient(135deg, #201040 0%, #100820 100%)',
        '#00f5d4': 'linear-gradient(135deg, #003d34 0%, #0a1a18 100%)',
    }
    
    col_donut, col_cards = st.columns([3, 2])
    
    with col_donut:
        # Hover data в _fmt_short формате
        abc_hover = []
        for _, r in abc_data.iterrows():
            abc_hover.append([
                r['ABC'], int(r['Заказов']), int(r['ЕО_кол']),
                _fmt_short(r['Сумма']), f"{r['Процент']:.1f}"
            ])
        
        fig_abc = go.Figure(go.Pie(
            labels=abc_data['ABC'],
            values=abc_data['Сумма'],
            hole=0.55,
            marker=dict(colors=abc_colors, line=dict(color='#020408', width=3)),
            textinfo='label+percent',
            textfont=dict(size=get_font_sizes()['donut_pct'], color='#ffffff'),
            insidetextorientation='horizontal',
            customdata=abc_hover,
            hovertemplate=(
                "<b>ABC: %{customdata[0]}</b><br>"
                "Сумма: %{customdata[3]} ₽<br>"
                "Доля: %{customdata[4]}%<br>"
                "Заказов: %{customdata[1]}<br>"
                "ЕО: %{customdata[2]}<extra></extra>"
            ),
        ))
        fig_abc.add_annotation(
            text=f"<b>{_fmt_short(abc_total)}</b><br><span style='font-size:14px'>₽ Факт</span>",
            x=0.5, y=0.5,
            font=dict(size=get_font_sizes()['donut_center'], color='#FFFFFF'),
            showarrow=False
        )
        fig_abc.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=get_big_font(), height=550, showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            hoverlabel=get_hover_style(),
        )
        st.plotly_chart(fig_abc, use_container_width=True, key="chart_abc_donut")
    
    with col_cards:
        st.markdown("#### По классам ABC")
        
        for _, row in abc_data.sort_values('Сумма', ascending=False).iterrows():
            color = abc_cm.get(row['ABC'], '#888')
            pct = row['Процент']
            bg = abc_bg_map.get(color, 'linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%)')
            st.markdown(f"""
            <div style="
                background: {bg};
                padding: 16px 20px; margin: 8px 0; border-radius: 10px;
                border-left: 5px solid {color};
                border: 1px solid {color}44;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:{color}; font-size:1.6rem; font-weight:bold;">{row['ABC']}</span>
                    <span style="color:{color}; font-size:1.4rem; font-weight:bold;">{pct:.1f}%</span>
                </div>
                <div style="color:#fff; font-size:1.1rem; margin-top:6px;">{_fmt_short(row['Сумма'])} ₽</div>
                <div style="color:#ccc; font-size:0.9rem; margin-top:4px;">
                    {int(row['Заказов'])} заказов &nbsp;•&nbsp; {int(row['ЕО_кол'])} ЕО
                </div>
                <div style="background:#333; border-radius:4px; height:6px; margin-top:8px;">
                    <div style="background:{color}; width:{min(pct, 100):.0f}%; height:6px; border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    _data_source("Fact_N (фактическая стоимость), группировка по полю ABC")
    
    selected_abc = st.selectbox("🔍 Фильтр по ABC:", options=[''] + list(abc_data['ABC'].values), key="select_abc")
    if selected_abc:
        st.session_state.extra_filters['abc'] = [selected_abc]
        st.info(f"✅ Фильтр ABC: {selected_abc}")
    
    st.markdown("---")
    
    # ========================================
    # 5. ПАРЕТО 80/20 — КОНЦЕНТРАЦИЯ ЗАТРАТ
    # ========================================
    st.markdown("### 📈 5. Парето: концентрация затрат (80/20)")
    
    if 'Fact_N' in df_f.columns:
        df_pareto = df_f[df_f['Fact_N'] > 0][['ID', 'Fact_N']].copy()
        df_pareto = df_pareto.sort_values('Fact_N', ascending=False).reset_index(drop=True)
        
        if len(df_pareto) > 0:
            df_pareto['cumsum'] = df_pareto['Fact_N'].cumsum()
            total = df_pareto['Fact_N'].sum()
            df_pareto['cum_pct'] = (df_pareto['cumsum'] / total * 100)
            df_pareto['order_pct'] = ((df_pareto.index + 1) / len(df_pareto) * 100)
            
            # Найти точку 80%
            idx_80 = (df_pareto['cum_pct'] >= 80).idxmax()
            pct_orders_80 = df_pareto.loc[idx_80, 'order_pct']
            n_orders_80 = idx_80 + 1
            
            fig_pareto = go.Figure()
            
            # Кумулятивная кривая
            fig_pareto.add_trace(go.Scatter(
                x=df_pareto['order_pct'],
                y=df_pareto['cum_pct'],
                mode='lines',
                line=dict(color='#00f5d4', width=3),
                fill='tozeroy',
                fillcolor='rgba(0,245,212,0.1)',
                name='Кумулятивная доля затрат',
                hovertemplate=(
                    "%{x:.1f}% заказов<br>"
                    "%{y:.1f}% затрат<extra></extra>"
                )
            ))
            
            # Линия 80%
            fig_pareto.add_hline(y=80, line_dash="dash", line_color="#ff0055", line_width=2,
                                 annotation_text="80% затрат", annotation_font_color="#ff0055")
            
            # Вертикальная линия — сколько % заказов дают 80%
            fig_pareto.add_vline(x=pct_orders_80, line_dash="dash", line_color="#ffd700", line_width=2,
                                 annotation_text=f"{pct_orders_80:.1f}% заказов",
                                 annotation_font_color="#ffd700",
                                 annotation_position="top right")
            
            # Диагональ — равномерное распределение
            fig_pareto.add_trace(go.Scatter(
                x=[0, 100], y=[0, 100],
                mode='lines',
                line=dict(color='#444444', width=1, dash='dot'),
                name='Равномерное',
                showlegend=True,
                hoverinfo='skip'
            ))
            
            fig_pareto.update_layout(**_base_layout(
                height=500,
                title=dict(text="Кривая Парето: концентрация фактических затрат", font=dict(size=get_font_sizes()['plotly_title'])),
                xaxis=dict(title="% заказов (от дорогих к дешёвым)", range=[0, 100],
                           tickfont=dict(size=get_font_sizes()['plotly_tick']), ticksuffix="%"),
                yaxis=dict(title="% кумулятивных затрат", range=[0, 105],
                           tickfont=dict(size=get_font_sizes()['plotly_tick']), ticksuffix="%"),
                legend=dict(orientation='h', y=-0.15, font=dict(size=get_font_sizes()['donut_legend'])),
            ))
            st.plotly_chart(fig_pareto, use_container_width=True, key="chart_pareto")
            
            # Вывод
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #1a1a2e 0%, #0a1628 100%);
                        padding:16px 20px; border-radius:10px; border-left:5px solid #00f5d4; margin:8px 0;">
                <div style="color:#00f5d4; font-size:1.3rem; font-weight:bold;">
                    📊 {pct_orders_80:.1f}% заказов → 80% затрат
                </div>
                <div style="color:#ccc; font-size:0.95rem; margin-top:6px;">
                    {n_orders_80} из {len(df_pareto)} заказов формируют 80% всех фактических расходов
                    ({_fmt_short(df_pareto.loc[idx_80, 'cumsum'])} ₽ из {_fmt_short(total)} ₽)
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            _data_source("Fact_N > 0, отсортировано по убыванию, кумулятивная сумма")
