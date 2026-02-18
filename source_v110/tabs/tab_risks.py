# -*- coding: utf-8 -*-
"""
TAB 6: РИСКИ (6 МЕТОДОВ)
========================

ИЗМЕНЕНИЯ v111:
- C2-M2: только по ЕО, без fallback по ТМ
"""

import streamlit as st
from config.font_config import render_metric_row
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.constants import METHODS_RISK
from utils.formatters import fmt, fmt_sign
from utils.export import create_excel_download
from components.charts import CHART_FONT, create_method_donut


def render_tab_risks(
    df_f: pd.DataFrame,
    agg_filtered: dict,
    method_thresholds: dict
) -> None:
    """Отрисовка вкладки Риски с 6 методами."""
    st.subheader("▣ Риск-скоринг: 6 методов")
    st.markdown(
        '<div class="dash-description">⚠️ <b>Риск-скоринг</b> — '
        '6 аналитических методов с настраиваемыми порогами. '
        'Risk_Sum учитывает вес каждого метода.</div>',
        unsafe_allow_html=True
    )
    
    # Общая статистика
    risk_orders = df_f[df_f['Risk_Sum'] > 0]
    
    risk_pct = len(risk_orders)/max(len(df_f),1)*100
    render_metric_row([
        ("ВСЕГО ЗАКАЗОВ", fmt(len(df_f))),
        ("С РИСКОМ (>0)", fmt(len(risk_orders)), f"{risk_pct:.1f}%", "#ff6b6b"),
        ("Σ РИСК-БАЛЛОВ", fmt(df_f['Risk_Sum'].sum())),
        ("СРЕДНИЙ БАЛЛ", f"{df_f['Risk_Sum'].mean():.2f}"),
    ])
    
    st.markdown("---")
    
    # Детализация по каждому методу
    for method_name, method_info in METHODS_RISK.items():
        flag = f"S_{method_name}"
        
        if flag in df_f.columns:
            triggered = df_f[df_f[flag] == True]
        else:
            triggered = pd.DataFrame()
        
        count = len(triggered)
        total_sum = triggered['Fact_N'].sum() if count > 0 else 0
        
        with st.expander(
            f"{method_info['icon']} {method_name} — "
            f"{count} срабатываний ({fmt(total_sum)} ₽)",
            expanded=True
        ):
            col_donut, col_desc, col_data = st.columns([0.6, 1, 2.5])
            
            with col_donut:
                fig_donut = create_method_donut(
                    count, len(df_f), method_name, color='#ff0055'
                )
                st.plotly_chart(
                    fig_donut, use_container_width=True,
                    key=f"donut_{method_name}"
                )
            
            with col_desc:
                st.markdown(f"### {method_info['icon']} {method_name}")
                st.markdown(f"*{method_info['desc']}*")
                st.markdown("---")
                st.markdown(method_info['full'])
                
                if method_info.get('has_threshold', False):
                    threshold_range = method_info.get('threshold_range', (0, 100))
                    current_value = method_thresholds.get(
                        method_name, method_info.get('threshold_default', 0)
                    )
                    
                    new_val = st.slider(
                        method_info.get('threshold_label', 'Порог'),
                        min_value=threshold_range[0],
                        max_value=threshold_range[1],
                        value=current_value,
                        key=f"slider_{method_name}"
                    )
                    
                    if new_val != method_thresholds.get(method_name):
                        st.session_state.method_thresholds[method_name] = new_val
                        st.rerun()
            
            with col_data:
                if count > 0:
                    export_df = _build_export_dataframe(
                        triggered, method_name, agg_filtered, method_thresholds
                    )
                    
                    display_df = export_df.head(50).copy()
                    
                    for col in ['Plan_N', 'Fact_N', 'Δ_₽', 'Медиана_ТМ_₽']:
                        if col in display_df.columns:
                            display_df[col] = display_df[col].apply(
                                lambda x: f"{x:,.0f}".replace(",", " ") if pd.notna(x) else ""
                            )
                    
                    st.dataframe(
                        display_df, use_container_width=True,
                        hide_index=True, height=450
                    )
                    
                    excel_method = create_excel_download(
                        export_df,
                        method_name.replace(':', '_').replace(' ', '_')
                    )
                    st.download_button(
                        f"📥 Excel ({method_name.split(':')[0]})",
                        data=excel_method,
                        file_name=f"{method_name.split(':')[0]}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{method_name}"
                    )
                else:
                    st.success(f"✓ Нет срабатываний по методу {method_name}")


def _build_export_dataframe(
    triggered: pd.DataFrame,
    method_name: str,
    agg_filtered: dict,
    method_thresholds: dict
) -> pd.DataFrame:
    """Формирует DataFrame с уникальными столбцами для каждого метода."""
    
    base_cols = ['ID', 'Текст', 'ТМ', 'Вид_Код', 'Вид', 'Plan_N', 'Fact_N', 'USER', 'РМ']
    export_df = triggered[[c for c in base_cols if c in triggered.columns]].copy()
    export_df['Δ_₽'] = triggered['Fact_N'] - triggered['Plan_N']
    
    # ========================================
    # C1-M1: ПЕРЕРАСХОД БЮДЖЕТА
    # ========================================
    if method_name == "C1-M1: Перерасход бюджета":
        export_df['Порог_%'] = method_thresholds.get(method_name, 20)
        export_df['Превышение_%'] = (
            (triggered['Fact_N'] / triggered['Plan_N'].replace(0, 1) - 1) * 100
        ).round(1)
        export_df = export_df.sort_values('Превышение_%', ascending=False)
    
    # ========================================
    # C1-M6: АНОМАЛИЯ ПО ИСТОРИИ ТМ
    # ========================================
    elif method_name == "C1-M6: Аномалия по истории ТМ":
        median_map = agg_filtered.get('median_by_tm', {})
        count_map = agg_filtered.get('count_by_tm', {})
        
        export_df['Медиана_ТМ_₽'] = triggered['ТМ'].map(median_map).fillna(0).round(0)
        export_df['Заказов_на_ТМ'] = triggered['ТМ'].map(count_map).fillna(0).astype(int)
        export_df['Коэфф_превышения'] = (
            triggered['Fact_N'] / export_df['Медиана_ТМ_₽'].replace(0, 1)
        ).round(2)
        export_df = export_df.sort_values(['ТМ', 'Коэфф_превышения'], ascending=[True, False])
    
    # ========================================
    # C1-M9: НЕЗАВЕРШЁННЫЕ РАБОТЫ
    # ========================================
    elif method_name == "C1-M9: Незавершённые работы":
        export_df['Статус'] = triggered['STAT']
        
        if 'Начало' in triggered.columns:
            export_df['План_начало'] = triggered['Начало'].dt.strftime('%Y-%m-%d')
            export_df['Дней_в_статусе'] = (
                pd.Timestamp.now() - triggered['Начало']
            ).dt.days
        if 'Конец' in triggered.columns:
            export_df['План_конец'] = triggered['Конец'].dt.strftime('%Y-%m-%d')
        
        if 'Дней_в_статусе' in export_df.columns:
            export_df = export_df.sort_values('Дней_в_статусе', ascending=False)
    
    # ========================================
    # C2-M2: ПРОБЛЕМНОЕ ОБОРУДОВАНИЕ
    # ТОЛЬКО по ЕО (без fallback по ТМ)
    # ========================================
    elif method_name == "C2-M2: Проблемное оборудование":
        count_by_eo = agg_filtered.get('count_by_eo', {})
        
        if 'EQUNR_Код' in triggered.columns:
            export_df['EQUNR_Код'] = triggered['EQUNR_Код']
        if 'ЕО' in triggered.columns:
            export_df['ЕО'] = triggered['ЕО']
        
        # Подсчёт заказов по ЕО
        if 'EQUNR_Код' in triggered.columns:
            export_df['Заказов_на_ЕО'] = triggered['EQUNR_Код'].map(count_by_eo).fillna(0).astype(int)
        elif 'ЕО' in triggered.columns:
            export_df['Заказов_на_ЕО'] = triggered['ЕО'].map(count_by_eo).fillna(0).astype(int)
        
        # Плановые сроки
        if 'Начало' in triggered.columns:
            export_df['План_начало'] = triggered['Начало'].dt.strftime('%Y-%m-%d')
        if 'Конец' in triggered.columns:
            export_df['План_конец'] = triggered['Конец'].dt.strftime('%Y-%m-%d')
        
        # Фактические сроки
        if 'Факт_Начало' in triggered.columns:
            export_df['Факт_начало'] = triggered['Факт_Начало'].dt.strftime('%Y-%m-%d')
        if 'Факт_Конец' in triggered.columns:
            export_df['Факт_конец'] = triggered['Факт_Конец'].dt.strftime('%Y-%m-%d')
        
        # Длительности
        if 'План_Длит' in triggered.columns:
            export_df['Дней_план'] = triggered['План_Длит'].fillna(0).astype(int)
        if 'Факт_Длит' in triggered.columns:
            export_df['Дней_факт'] = triggered['Факт_Длит'].fillna(0).astype(int)
        
        # Сортировка по количеству заказов на ЕО
        if 'Заказов_на_ЕО' in export_df.columns:
            export_df = export_df.sort_values('Заказов_на_ЕО', ascending=False)
    
    # ========================================
    # NEW-9: ФОРМАЛЬНОЕ ЗАКРЫТИЕ В ДЕКАБРЕ
    # ========================================
    elif method_name == "NEW-9: Формальное закрытие в декабре":
        if 'Начало' in triggered.columns:
            export_df['План_начало'] = triggered['Начало'].dt.strftime('%Y-%m-%d')
        if 'Конец' in triggered.columns:
            export_df['План_конец'] = triggered['Конец'].dt.strftime('%Y-%m-%d')
            export_df['План_месяц'] = triggered['Конец'].dt.month
        if 'Факт_Начало' in triggered.columns:
            export_df['Факт_начало'] = triggered['Факт_Начало'].dt.strftime('%Y-%m-%d')
        if 'Факт_Конец' in triggered.columns:
            export_df['Факт_конец'] = triggered['Факт_Конец'].dt.strftime('%Y-%m-%d')
            export_df['Факт_день'] = triggered['Факт_Конец'].dt.day
        if 'План_Длит' in triggered.columns:
            export_df['Дней_план'] = triggered['План_Длит'].fillna(0).astype(int)
        if 'Факт_Длит' in triggered.columns:
            export_df['Дней_факт'] = triggered['Факт_Длит'].fillna(0).astype(int)
        if 'План_Длит' in triggered.columns and 'Факт_Длит' in triggered.columns:
            export_df['Быстрота_%'] = (
                triggered['Факт_Длит'] / triggered['План_Длит'].replace(0, 1) * 100
            ).round(1)
        if 'Быстрота_%' in export_df.columns:
            export_df = export_df.sort_values('Быстрота_%', ascending=True)
    
    # ========================================
    # NEW-10: ВОЗВРАТЫ СТАТУСОВ
    # ========================================
    elif method_name == "NEW-10: Возвраты статусов":
        if 'N_STATUS_RETURNS' in triggered.columns:
            export_df['Кол_во_возвратов'] = triggered['N_STATUS_RETURNS']
        if 'ALL_STATUSES' in triggered.columns:
            export_df['Все_статусы'] = triggered['ALL_STATUSES']
        if 'STAT' in triggered.columns:
            export_df['Текущий_статус'] = triggered['STAT']
        if 'Кол_во_возвратов' in export_df.columns:
            export_df = export_df.sort_values('Кол_во_возвратов', ascending=False)
    
    return export_df
