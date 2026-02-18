# -*- coding: utf-8 -*-
"""
tabs/tab_planners.py — TAB 4: ПЛАНОВИКИ v112.3

KPI → Heatmap-таблица (Факт/План/Отклонение) → HEATMAP методов → Excel
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.constants import METHODS_RISK
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


def render_tab_planners(df_f):
    st.subheader("▣ Аналитика по плановикам")
    st.markdown(
        '<div class="dash-description">👥 <b>Плановики</b> — '
        'кто сколько потратил, перерасход, количество заказов.</div>',
        unsafe_allow_html=True)

    # ==== KPI ====
    total_plan = df_f['Plan_N'].sum() if 'Plan_N' in df_f.columns else 0
    total_fact = df_f['Fact_N'].sum() if 'Fact_N' in df_f.columns else 0
    n_ingrp = df_f['INGRP'].nunique() if 'INGRP' in df_f.columns else 0
    n_users = df_f['USER'].nunique() if 'USER' in df_f.columns else 0
    overrun = len(df_f[df_f['Fact_N'] > df_f['Plan_N']]) if 'Plan_N' in df_f.columns else 0

    render_metric_row([
        ("ГРУПП ПЛАНОВИКОВ", fmt(n_ingrp)),
        ("АВТОРОВ (USER)", fmt(n_users)),
        ("ФАКТ (Σ)", _fmt_short(total_fact) + " ₽"),
        ("С ПЕРЕРАСХОДОМ", fmt(overrun) + " зак."),
    ])

    st.markdown("---")

    # ==== 1. ГРУППЫ ПЛАНОВИКОВ ====
    st.markdown("### 👥 1. Группы плановиков (INGRP)")

    if 'INGRP' in df_f.columns:
        ingrp = df_f.groupby('INGRP').agg(
            Заказов=('ID', 'count'), Факт=('Fact_N', 'sum'), План=('Plan_N', 'sum')
        ).reset_index()
        if 'ЕО' in df_f.columns:
            eo = df_f.groupby('INGRP')['ЕО'].nunique().reset_index()
            eo.columns = ['INGRP', 'ЕО_кол']
            ingrp = ingrp.merge(eo, on='INGRP', how='left')
        else:
            ingrp['ЕО_кол'] = 0
        ingrp['Отклонение'] = ingrp['Факт'] - ingrp['План']
        ingrp = ingrp.sort_values('Отклонение', ascending=False)

        render_unified_heatmap(ingrp, 'INGRP', 'ingrp', extra_cols=[('ЕО_кол', 'ЕО', 'center')] if 'ЕО_кол' in ingrp.columns else None)
        _data_source("Отклонение = Fact_N − Plan_N, группировка по INGRP")
        
        # Сводная аналитика: donut + bars
        st.markdown("#### 📊 Сводная по группам")
        col_d, col_b = st.columns([2, 3])
        
        with col_d:
            donut_colors = ['#ff0055', '#ffd700', '#10b981', '#4a9eff', '#8b5cf6',
                            '#ff6b35', '#06b6d4', '#f472b6', '#a78bfa', '#34d399']
            ingrp_top = ingrp.sort_values('Факт', ascending=False)
            fig_d = go.Figure(go.Pie(
                labels=ingrp_top['INGRP'], values=ingrp_top['Факт'], hole=0.55,
                marker=dict(colors=donut_colors[:len(ingrp_top)], line=dict(color='#020408', width=2)),
                textinfo='percent', textposition='outside',
                textfont=dict(size=get_font_sizes()['donut_pct'], color='#fff'),
                hovertemplate="<b>%{label}</b><br>Факт: %{value:,.0f} ₽<br>%{percent}<extra></extra>",
            ))
            fig_d.add_annotation(text=f"<b>{_fmt_short(ingrp['Факт'].sum())}</b><br><span style='font-size:14px'>₽ Факт</span>",
                                 x=0.5, y=0.5, font=dict(size=get_font_sizes()['donut_center'], color='#FFF'), showarrow=False)
            fig_d.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=get_big_font(), height=450,
                                showlegend=True, legend=dict(font=dict(size=get_font_sizes()['donut_legend'], color='#ccc'), orientation='h', y=-0.1),
                                margin=dict(l=30, r=30, t=30, b=60), hoverlabel=get_hover_style())
            st.plotly_chart(fig_d, use_container_width=True, key="chart_ingrp_donut")
        
        with col_b:
            ingrp_bars = ingrp.sort_values('Заказов', ascending=True)
            fig_b = go.Figure(go.Bar(
                y=ingrp_bars['INGRP'].str[:35], x=ingrp_bars['Заказов'], orientation='h',
                marker=dict(color='#4a9eff', line=dict(color='#fff', width=1)),
                text=[f"{int(v)} зак. • {_fmt_short(f)} ₽" for v, f in zip(ingrp_bars['Заказов'], ingrp_bars['Факт'])],
                textposition='outside', textfont=dict(size=get_font_sizes()['bar_label'], color='#ccc'),
                hovertemplate="<b>%{y}</b><br>Заказов: %{x}<extra></extra>"
            ))
            fig_b.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                font=get_big_font(), height=max(350, len(ingrp_bars)*35+80),
                                yaxis=dict(categoryorder='total ascending', tickfont=dict(size=get_font_sizes()['plotly_tick'])),
                                xaxis=dict(title="Заказов", tickfont=dict(size=get_font_sizes()['plotly_tick'])),
                                margin=dict(l=250, r=120, t=30, b=40), hoverlabel=get_hover_style())
            st.plotly_chart(fig_b, use_container_width=True, key="chart_ingrp_bars")

        with st.expander(f"📋 Таблица всех групп ({len(ingrp)})", expanded=False):
            tbl = ingrp.copy()
            tbl['План'] = tbl['План'].apply(lambda x: f"{fmt(x)} ₽")
            tbl['Факт'] = tbl['Факт'].apply(lambda x: f"{fmt(x)} ₽")
            tbl['Отклонение'] = tbl['Отклонение'].apply(fmt_sign)
            st.dataframe(tbl, use_container_width=True, hide_index=True, height=400)
            excel = create_excel_download(ingrp, "ingrp")
            st.download_button("📥 Excel (группы)", data=excel,
                               file_name=f"ingrp_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="dl_ingrp")
    else:
        st.warning("Поле INGRP отсутствует")

    st.markdown("---")

    # ==== 2. АВТОРЫ (USER) ====
    st.markdown("### 🧑‍💼 2. Авторы заказов (USER)")

    if 'USER' in df_f.columns:
        users = df_f.groupby('USER').agg(
            Заказов=('ID', 'count'), Факт=('Fact_N', 'sum'), План=('Plan_N', 'sum')
        ).reset_index()
        users['Отклонение'] = users['Факт'] - users['План']
        top_users = users.sort_values('Отклонение', ascending=False).head(20)

        render_unified_heatmap(top_users, 'USER', 'user')
        _data_source("Отклонение = Fact_N − Plan_N, TOP-20 авторов по USER")
    else:
        st.warning("Поле USER отсутствует")

    st.markdown("---")

    # ==== 3. HEATMAP: Плановик × Метод риска ====
    st.markdown("### 🗺️ 3. HEATMAP: Группа плановиков × Метод риска")

    if 'INGRP' in df_f.columns:
        heatmap_data = []
        for method_name in METHODS_RISK.keys():
            flag = f"S_{method_name}"
            if flag in df_f.columns:
                method_by_ingrp = df_f.groupby('INGRP')[flag].sum().to_dict()
                for ingrp_name, count in method_by_ingrp.items():
                    if count > 0:
                        heatmap_data.append({
                            'INGRP': ingrp_name,
                            'Метод': method_name.split(':')[0],
                            'Количество': count
                        })

        if heatmap_data:
            hm_df = pd.DataFrame(heatmap_data)
            hm_pivot = hm_df.pivot_table(index='INGRP', columns='Метод', values='Количество', fill_value=0)
            hm_pivot['_total'] = hm_pivot.sum(axis=1)
            hm_pivot = hm_pivot.sort_values('_total', ascending=False).head(15).drop('_total', axis=1)

            fig_hm = go.Figure(go.Heatmap(
                z=hm_pivot.values, x=hm_pivot.columns, y=hm_pivot.index,
                colorscale=[[0, '#0a0a1a'], [0.5, '#ffd700'], [1, '#ff0055']],
                text=hm_pivot.values, texttemplate="%{text}",
                textfont=dict(size=get_font_sizes()['bar_label'], color='white')
            ))
            fig_hm.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=get_big_font(), height=500,
                xaxis=dict(tickangle=45), margin=dict(l=200, b=120),
                hoverlabel=get_hover_style(),
            )
            st.plotly_chart(fig_hm, use_container_width=True, key="chart_heatmap_planners")
            _data_source("Количество сработавших методов по S_* флагам, группировка по INGRP")
        else:
            st.info("Нет данных для HEATMAP")

    st.markdown("---")

    # ==== Выгрузка проблемных ====
    st.markdown("### 📥 Проблемные заказы по плановикам")
    cols_show = [c for c in ['ID', 'Текст', 'INGRP', 'USER', 'ТМ', 'Plan_N', 'Fact_N', 'Risk_Sum'] if c in df_f.columns]
    problem = df_f[df_f['Risk_Sum'] > 0][cols_show].sort_values('Risk_Sum', ascending=False)
    if len(problem) > 0:
        st.dataframe(problem.head(100), use_container_width=True, hide_index=True, height=300)
        excel_p = create_excel_download(problem, "planners_problems")
        st.download_button("📥 Excel (проблемные)", data=excel_p,
                           file_name=f"planners_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_planners")
    else:
        st.success("✓ Нет проблемных заказов")
