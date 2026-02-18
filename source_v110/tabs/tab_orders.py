# -*- coding: utf-8 -*-
"""
tabs/tab_orders.py — TAB 8: ПРОСМОТР ЗАКАЗОВ v112.4

Быстрые фильтры-теги (USER, INGRP, ЦЕХ, Вид, РМ, ABC) + таблица + Excel.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from config.constants import METHODS_RISK
from utils.formatters import fmt, fmt_sign
from utils.export import create_excel_download
from config.font_config import render_metric_row


def render_tab_orders(df_f: pd.DataFrame) -> None:
    st.subheader("▣ Просмотр заказов")
    st.markdown(
        '<div class="dash-description">📋 <b>Просмотр заказов</b> — '
        'быстрые фильтры по USER, плановику, цеху, виду работ. '
        'Детализация сроков, отклонений и сработавших методов риска.</div>',
        unsafe_allow_html=True
    )

    # ========================================
    # БЫСТРЫЕ ФИЛЬТРЫ-ТЕГИ (в форме — без rerun)
    # ========================================
    st.markdown("### 🏷️ Быстрые фильтры")
    
    # Собираем доступные поля для тегов
    tag_fields = []
    for col, label in [('USER', '👤 Автор'), ('INGRP', '👥 Группа плановиков'),
                        ('ЦЕХ', '🏭 Цех'), ('Вид', '🔧 Вид работ'),
                        ('РМ', '🏗️ Рабочее место'), ('ABC', '📦 ABC'),
                        ('STAT', '📊 Статус')]:
        if col in df_f.columns:
            tag_fields.append((col, label))
    
    if 'orders_applied_tags' not in st.session_state:
        st.session_state.orders_applied_tags = {}
    if 'orders_risk_f' not in st.session_state:
        st.session_state.orders_risk_f = "Все заказы"
    if 'orders_method_f' not in st.session_state:
        st.session_state.orders_method_f = "Все методы"
    if 'orders_sort_f' not in st.session_state:
        st.session_state.orders_sort_f = "По риску (убыв.)"
    
    with st.form(key="orders_all_filters_form"):
        # Ряд 1: Теги
        tag_col1, tag_col2 = st.columns([1, 3])
        
        with tag_col1:
            if tag_fields:
                tag_labels = [label for _, label in tag_fields]
                selected_label = st.selectbox("Фильтр по:", tag_labels, key="tag_field_sel")
                selected_field = [col for col, label in tag_fields if label == selected_label][0]
            else:
                selected_field = None
        
        with tag_col2:
            if selected_field:
                unique_vals = df_f[selected_field].dropna().unique()
                val_counts = df_f[selected_field].value_counts().to_dict()
                options = sorted([str(v) for v in unique_vals if str(v) != 'Н/Д' and str(v).strip() != ''])
                selected_tags = st.multiselect(
                    f"Выберите значения ({len(options)} доступно):",
                    options=options,
                    format_func=lambda x: f"{x} ({val_counts.get(x, 0)})",
                    key="tag_vals_sel"
                )
            else:
                selected_tags = []
        
        # Ряд 2: Риск, Метод, Сортировка
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            risk_filter = st.radio(
                "Показать:", ["Все заказы", "Только с риском (>0)", "Только без риска"],
                horizontal=True, key="orders_risk_filter",
                index=["Все заказы", "Только с риском (>0)", "Только без риска"].index(st.session_state.orders_risk_f)
            )
        
        with col_f2:
            method_options = ["Все методы"] + list(METHODS_RISK.keys())
            m_idx = method_options.index(st.session_state.orders_method_f) if st.session_state.orders_method_f in method_options else 0
            selected_method = st.selectbox("Фильтр по методу:", options=method_options, key="orders_method_filter", index=m_idx)
        
        with col_f3:
            sort_options_list = ["По риску (убыв.)", "По риску (возр.)", "По факту (убыв.)",
                                 "По отклонению (убыв.)", "По превышению сроков (убыв.)"]
            s_idx = sort_options_list.index(st.session_state.orders_sort_f) if st.session_state.orders_sort_f in sort_options_list else 0
            sort_choice = st.selectbox("Сортировка:", options=sort_options_list, key="orders_sort", index=s_idx)
        
        # Кнопки
        btn1, btn2, _ = st.columns([1, 1, 4])
        with btn1:
            apply_submitted = st.form_submit_button("🔍 Применить", type="primary")
        with btn2:
            reset_submitted = st.form_submit_button("🗑️ Сбросить всё")
    
    sort_options = {
        "По риску (убыв.)": ("Risk_Sum", False),
        "По риску (возр.)": ("Risk_Sum", True),
        "По факту (убыв.)": ("Fact_N", False),
        "По отклонению (убыв.)": ("Δ_Сумма", False),
        "По превышению сроков (убыв.)": ("Δ_Дней", False),
    }
    
    if reset_submitted:
        st.session_state.orders_applied_tags = {}
        st.session_state.orders_risk_f = "Все заказы"
        st.session_state.orders_method_f = "Все методы"
        st.session_state.orders_sort_f = "По риску (убыв.)"
        risk_filter = "Все заказы"
        selected_method = "Все методы"
        sort_choice = "По риску (убыв.)"
    elif apply_submitted:
        if selected_field and selected_tags:
            st.session_state.orders_applied_tags = {selected_field: selected_tags}
        else:
            st.session_state.orders_applied_tags = {}
        st.session_state.orders_risk_f = risk_filter
        st.session_state.orders_method_f = selected_method
        st.session_state.orders_sort_f = sort_choice
    else:
        # Не нажато — используем сохранённые
        risk_filter = st.session_state.orders_risk_f
        selected_method = st.session_state.orders_method_f
        sort_choice = st.session_state.orders_sort_f
    
    active_tags = st.session_state.orders_applied_tags
    
    if active_tags:
        tags_display = ' • '.join([f"**{k}**: {', '.join(v)}" for k, v in active_tags.items()])
        st.success(f"🏷️ Активный фильтр: {tags_display}")

    # ========================================
    # ПОДГОТОВКА ДАННЫХ
    # ========================================
    df_view = df_f.copy()
    
    # Применяем теги-фильтры
    for field, values in active_tags.items():
        df_view = df_view[df_view[field].astype(str).isin(values)]
    
    df_view['Δ_Сумма'] = df_view['Fact_N'] - df_view['Plan_N']
    
    if 'План_Длит' in df_view.columns and 'Факт_Длит' in df_view.columns:
        df_view['Δ_Дней'] = pd.to_numeric(df_view['Факт_Длит'], errors='coerce') - \
                           pd.to_numeric(df_view['План_Длит'], errors='coerce')
    else:
        df_view['Δ_Дней'] = 0
    
    def get_triggered_methods(row):
        triggered = []
        for method_name in METHODS_RISK.keys():
            flag = f"S_{method_name}"
            if flag in row and row[flag] == True:
                triggered.append(method_name.split(':')[0])
        return ', '.join(triggered) if triggered else '—'
    
    df_view['Сработавшие_методы'] = df_view.apply(get_triggered_methods, axis=1)
    
    # Фильтр по риску
    if risk_filter == "Только с риском (>0)":
        df_view = df_view[df_view['Risk_Sum'] > 0]
    elif risk_filter == "Только без риска":
        df_view = df_view[df_view['Risk_Sum'] == 0]
    
    # Фильтр по методу
    if selected_method != "Все методы":
        flag = f"S_{selected_method}"
        if flag in df_view.columns:
            df_view = df_view[df_view[flag] == True]
    
    # Сортировка
    sort_col, sort_asc = sort_options[sort_choice]
    if sort_col in df_view.columns:
        df_view = df_view.sort_values(sort_col, ascending=sort_asc)

    # ========================================
    # АКТИВНЫЕ ФИЛЬТРЫ — ИНФОРМАЦИОННАЯ ПАНЕЛЬ
    # ========================================
    if active_tags:
        tags_info = ' • '.join([f"**{k}**: {', '.join(v)}" for k, v in active_tags.items()])
        st.info(f"🏷️ Активные фильтры: {tags_info} → **{len(df_view)}** заказов")

    # ========================================
    # KPI
    # ========================================
    avg_delay = df_view['Δ_Дней'].mean() if 'Δ_Дней' in df_view.columns else 0
    render_metric_row([
        ("ВСЕГО", fmt(len(df_view))),
        ("С РИСКОМ", fmt(len(df_view[df_view['Risk_Sum'] > 0]))),
        ("Σ ФАКТ", f"{fmt(df_view['Fact_N'].sum())} ₽"),
        ("Σ ОТКЛОНЕНИЕ", f"{fmt_sign(df_view['Δ_Сумма'].sum())} ₽"),
        ("СР. ПРЕВЫШ. СРОКОВ", f"{avg_delay:.1f} дн."),
    ])

    st.markdown("---")

    # ========================================
    # МИНИ-СВОДКА ПО ВЫБРАННОМУ ФИЛЬТРУ
    # ========================================
    if active_tags:
        for field, values in active_tags.items():
            if len(values) <= 5:
                st.markdown(f"#### 📊 Сводка по {field}")
                summary_data = df_view.groupby(field).agg(
                    Заказов=('ID', 'count'),
                    Факт=('Fact_N', 'sum'),
                    План=('Plan_N', 'sum'),
                    Риск=('Risk_Sum', 'sum')
                ).reset_index()
                summary_data['Отклонение'] = summary_data['Факт'] - summary_data['План']
                
                for _, sr in summary_data.iterrows():
                    dev = sr['Отклонение']
                    dev_color = '#ff6b6b' if dev > 0 else '#6bffb8'
                    dev_sign = '+' if dev > 0 else ''
                    st.markdown(f"""
                    <div style="background:#1a1a2e; padding:12px 18px; border-radius:8px; 
                                margin:6px 0; border-left:4px solid {dev_color};">
                        <span style="color:#fff; font-size:1.1rem; font-weight:bold;">{sr[field]}</span>
                        <span style="color:#ccc; font-size:0.9rem; margin-left:20px;">
                            {int(sr['Заказов'])} заказов &nbsp;•&nbsp; 
                            Факт: {fmt(sr['Факт'])} ₽ &nbsp;•&nbsp;
                            <span style="color:{dev_color}; font-weight:bold;">{dev_sign}{fmt(dev)} ₽</span>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("---")

    # ========================================
    # ТАБЛИЦА ЗАКАЗОВ
    # ========================================
    columns_order = [
        'ID', 'Текст', 'ТМ', 'ЕО', 'Вид', 'STAT', 'ABC',
        'Plan_N', 'Fact_N', 'Δ_Сумма',
        'Начало', 'Конец', 'Факт_Начало', 'Факт_Конец',
        'План_Длит', 'Факт_Длит', 'Δ_Дней',
        'Risk_Sum', 'Сработавшие_методы',
        'INGRP', 'USER', 'РМ', 'ЗАВОД', 'УСТАНОВКА', 'БЕ'
    ]
    columns_exist = [c for c in columns_order if c in df_view.columns]
    df_display = df_view[columns_exist].copy()
    
    rename_map = {
        'ID': 'Заказ', 'Plan_N': 'План ₽', 'Fact_N': 'Факт ₽',
        'Δ_Сумма': 'Δ ₽', 'План_Длит': 'План дн.', 'Факт_Длит': 'Факт дн.',
        'Δ_Дней': 'Δ дн.', 'Risk_Sum': 'Риск', 'Сработавшие_методы': 'Методы'
    }
    df_display = df_display.rename(columns={k: v for k, v in rename_map.items() if k in df_display.columns})
    
    display_df = df_display.copy()
    for col in ['План ₽', 'Факт ₽']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: fmt(x) if pd.notna(x) else '—')
    if 'Δ ₽' in display_df.columns:
        display_df['Δ ₽'] = display_df['Δ ₽'].apply(lambda x: fmt_sign(x) if pd.notna(x) else '—')
    for col in ['План дн.', 'Факт дн.', 'Δ дн.']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{int(x)}" if pd.notna(x) else '—')
    for col in ['Начало', 'Конец', 'Факт_Начало', 'Факт_Конец']:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.strftime('%Y-%m-%d')
            display_df[col] = display_df[col].fillna('—')

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=600)

    # ========================================
    # ВЫГРУЗКА
    # ========================================
    st.markdown("### 📥 Выгрузка")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        excel_view = create_excel_download(df_display, "orders_view")
        st.download_button("📥 Excel (текущий вид)", data=excel_view,
                           file_name=f"orders_view_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_orders_view")
    with col_dl2:
        excel_full = create_excel_download(df_view, "orders_full")
        st.download_button("📥 Excel (все колонки)", data=excel_full,
                           file_name=f"orders_full_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_orders_full")
