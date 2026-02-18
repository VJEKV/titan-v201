# -*- coding: utf-8 -*-
"""
components/sidebar.py — Боковая панель фильтров

ИЗМЕНЕНИЯ v111.2:
- Иерархические фильтры: кнопка "Применить" вместо мгновенного применения
- Можно выбрать несколько значений и применить все разом
"""

import streamlit as st
import pandas as pd

from config.constants import HIERARCHY_LEVELS
from config.settings import reset_all_filters
from utils.filters import get_hierarchy_options, apply_hierarchy_filters


def render_sidebar(df):
    """Отрисовка боковой панели с фильтрами."""
    
    # ========================================
    # РАЗМЕР ШРИФТА (без rerun — читается всеми вкладками)
    # ========================================
    if 'font_size' not in st.session_state:
        st.session_state.font_size = 'L'
    
    st.sidebar.markdown("## 🔤 РАЗМЕР ШРИФТА")
    font_choice = st.sidebar.radio(
        "Выберите:", ['S', 'M', 'L'],
        index=['S', 'M', 'L'].index(st.session_state.font_size),
        horizontal=True, key="font_size_radio",
        label_visibility="collapsed"
    )
    st.session_state.font_size = font_choice
    
    st.sidebar.divider()
    
    # ========================================
    # СЕКЦИЯ 1: ПОИСК И ПЕРИОД
    # ========================================
    st.sidebar.markdown("## 🔍 ПОИСК И ПЕРИОД")
    
    f_search = st.sidebar.text_input(
        "Поиск по тексту",
        value=st.session_state.extra_filters.get('search', ''),
        placeholder="Номер заказа, текст...",
        key="filter_search_main"
    )
    st.session_state.extra_filters['search'] = f_search
    
    # Фильтр по датам
    if 'Конец' in df.columns:
        dates = df['Конец'].dropna()
        if len(dates) > 0:
            min_date, max_date = dates.min().date(), dates.max().date()
            col1, col2 = st.sidebar.columns(2)
            with col1:
                f_date_from = st.date_input(
                    "От",
                    value=st.session_state.extra_filters.get('date_from') or min_date,
                    min_value=min_date, max_value=max_date,
                    key="filter_date_from_main"
                )
            with col2:
                f_date_to = st.date_input(
                    "До",
                    value=st.session_state.extra_filters.get('date_to') or max_date,
                    min_value=min_date, max_value=max_date,
                    key="filter_date_to_main"
                )
            st.session_state.extra_filters['date_from'] = f_date_from
            st.session_state.extra_filters['date_to'] = f_date_to
    
    st.sidebar.divider()
    
    # ========================================
    # СЕКЦИЯ 2: ИЕРАРХИЯ ОБЪЕКТОВ
    # Выбор через multiselect, применение через кнопку
    # ========================================
    st.sidebar.markdown("## 🏗️ ИЕРАРХИЯ ОБЪЕКТОВ")
    
    # Инициализируем временное хранилище для "черновых" выборов
    if '_pending_hierarchy' not in st.session_state:
        st.session_state._pending_hierarchy = {
            level['key']: list(st.session_state.hierarchy_filters.get(level['key'], []))
            for level in HIERARCHY_LEVELS
        }
    
    def get_parent_filters_pending(current_level_idx):
        """Родительские фильтры из ПРИМЕНЁННЫХ (не pending)."""
        parents = {}
        for i in range(current_level_idx):
            key = HIERARCHY_LEVELS[i]['key']
            if st.session_state.hierarchy_filters.get(key):
                parents[key] = st.session_state.hierarchy_filters[key]
        return parents
    
    pending_changed = False
    
    for i, level in enumerate(HIERARCHY_LEVELS):
        key = level['key']
        name = level['name']
        icon = level['icon']
        
        parent_filters = get_parent_filters_pending(i)
        options = get_hierarchy_options(df, key, parent_filters)
        
        label = f"{icon} {name} ({len(options)})" if options else f"{icon} {name} (нет)"
        
        if options:
            # Текущие применённые значения
            current_applied = st.session_state.hierarchy_filters.get(key, [])
            default_vals = [x for x in current_applied if x in options]
            
            selected = st.sidebar.multiselect(
                label, options=options, default=default_vals,
                key=f"hier_{key}_main"
            )
            st.session_state._pending_hierarchy[key] = selected
            
            # Проверяем изменились ли
            if set(selected) != set(current_applied):
                pending_changed = True
        else:
            st.sidebar.text(f"{icon} {name}: нет данных")
            st.session_state._pending_hierarchy[key] = []
    
    # Кнопка "Применить фильтры" — только если есть изменения
    col_apply, col_clear = st.sidebar.columns(2)
    
    with col_apply:
        if st.button(
            "✅ Применить" if pending_changed else "✅ Применено",
            use_container_width=True,
            key="apply_hierarchy",
            disabled=not pending_changed,
            type="primary" if pending_changed else "secondary"
        ):
            for level in HIERARCHY_LEVELS:
                key = level['key']
                st.session_state.hierarchy_filters[key] = list(
                    st.session_state._pending_hierarchy.get(key, [])
                )
            st.rerun()
    
    with col_clear:
        has_any_filter = any(
            st.session_state.hierarchy_filters.get(level['key'], [])
            for level in HIERARCHY_LEVELS
        )
        if st.button(
            "🗑 Очистить",
            use_container_width=True,
            key="clear_hierarchy",
            disabled=not has_any_filter
        ):
            for level in HIERARCHY_LEVELS:
                st.session_state.hierarchy_filters[level['key']] = []
                st.session_state._pending_hierarchy[level['key']] = []
            st.rerun()
    
    if pending_changed:
        st.sidebar.caption("⚡ Выберите все нужные значения, затем нажмите «Применить»")
    
    st.sidebar.divider()
    
    # ========================================
    # СЕКЦИЯ 3: КЛАССИФИКАЦИЯ (expander)
    # ========================================
    with st.sidebar.expander("📋 КЛАССИФИКАЦИЯ", expanded=False):
        df_for_options = apply_hierarchy_filters(df, st.session_state.hierarchy_filters)
        
        # Вид заказа
        if 'Вид_Код' in df_for_options.columns and 'Вид' in df_for_options.columns:
            vid_pairs = df_for_options[['Вид_Код', 'Вид']].drop_duplicates()
            vid_pairs = vid_pairs[vid_pairs['Вид_Код'] != 'Н/Д']
            
            vid_options = []
            code_to_display = {}
            for _, row in vid_pairs.iterrows():
                code = row['Вид_Код']
                name = row['Вид']
                display = f"{code} - {name}"
                vid_options.append(display)
                code_to_display[code] = display
            
            vid_options = sorted(vid_options)
            saved_codes = st.session_state.extra_filters.get('vid_kod', [])
            default_display = [code_to_display.get(c) for c in saved_codes if c in code_to_display]
            default_display = [d for d in default_display if d]
            
            f_vid_display = st.multiselect(
                "Вид заказа", options=vid_options, default=default_display,
                key="filter_vid_main"
            )
            selected_codes = [opt.split(' - ')[0] for opt in f_vid_display]
            st.session_state.extra_filters['vid_kod'] = selected_codes
        else:
            all_vid = sorted([x for x in df_for_options['Вид'].unique() if x != 'Н/Д'])
            f_vid = st.multiselect(
                "Вид заказа", options=all_vid,
                default=[x for x in st.session_state.extra_filters.get('vid', []) if x in all_vid],
                key="filter_vid_main"
            )
            st.session_state.extra_filters['vid'] = f_vid
        
        # ABC
        all_abc = sorted([x for x in df_for_options['ABC'].unique() if x != 'Н/Д'])
        f_abc = st.multiselect(
            "Критичность ABC", options=all_abc,
            default=[x for x in st.session_state.extra_filters.get('abc', []) if x in all_abc],
            key="filter_abc_main"
        )
        st.session_state.extra_filters['abc'] = f_abc
        
        # Статус
        all_stat = sorted([x for x in df_for_options['STAT'].unique() if x != 'Н/Д'])
        f_stat = st.multiselect(
            "Системный статус", options=all_stat,
            default=[x for x in st.session_state.extra_filters.get('stat', []) if x in all_stat],
            key="filter_stat_main"
        )
        st.session_state.extra_filters['stat'] = f_stat
        
        # Класс оборудования
        if 'КЛАСС' in df_for_options.columns:
            all_klass = sorted([x for x in df_for_options['КЛАСС'].unique() if x != 'Н/Д'])
            if all_klass:
                f_klass = st.multiselect(
                    "Класс оборудования", options=all_klass,
                    default=[x for x in st.session_state.extra_filters.get('klass', []) if x in all_klass],
                    key="filter_klass_main"
                )
                st.session_state.extra_filters['klass'] = f_klass
    
    # ========================================
    # СЕКЦИЯ 4: РАБОЧИЕ МЕСТА
    # ========================================
    with st.sidebar.expander("🔧 РАБОЧИЕ МЕСТА", expanded=False):
        if 'РМ' in df_for_options.columns:
            all_rm = sorted([x for x in df_for_options['РМ'].unique() if x != 'Н/Д'])
            if all_rm:
                f_rm = st.multiselect(
                    "Рабочее место", options=all_rm,
                    default=[x for x in st.session_state.extra_filters.get('rm', []) if x in all_rm],
                    key="filter_rm_main"
                )
                st.session_state.extra_filters['rm'] = f_rm
        
        if 'МЕСТОПОЛ' in df_for_options.columns:
            all_mestopol = sorted([x for x in df_for_options['МЕСТОПОЛ'].unique() if x != 'Н/Д'])
            if all_mestopol:
                f_mestopol = st.multiselect(
                    "Местоположение", options=all_mestopol,
                    default=[x for x in st.session_state.extra_filters.get('mestopol', []) if x in all_mestopol],
                    key="filter_mestopol_main"
                )
                st.session_state.extra_filters['mestopol'] = f_mestopol
        
        if 'INGRP' in df_for_options.columns:
            all_ingrp = sorted([x for x in df_for_options['INGRP'].unique() if x != 'Н/Д'])
            if all_ingrp:
                f_ingrp = st.multiselect(
                    "Группа плановиков", options=all_ingrp,
                    default=[x for x in st.session_state.extra_filters.get('ingrp', []) if x in all_ingrp],
                    key="filter_ingrp_main"
                )
                st.session_state.extra_filters['ingrp'] = f_ingrp
    
    # ========================================
    # СЕКЦИЯ 5: ДОКУМЕНТЫ
    # ========================================
    with st.sidebar.expander("📄 ДОКУМЕНТЫ", expanded=False):
        if 'MAUFNR' in df_for_options.columns:
            all_maufnr = sorted([x for x in df_for_options['MAUFNR'].unique() if x != 'Н/Д'])
            if all_maufnr and len(all_maufnr) < 500:
                f_maufnr = st.multiselect(
                    "Ведущий заказ", options=all_maufnr,
                    default=[x for x in st.session_state.extra_filters.get('maufnr', []) if x in all_maufnr],
                    key="filter_maufnr_main"
                )
                st.session_state.extra_filters['maufnr'] = f_maufnr
        
        if 'ВИД_РАБОТ' in df_for_options.columns:
            all_vid_rabot = sorted([x for x in df_for_options['ВИД_РАБОТ'].unique() if x != 'Н/Д'])
            if all_vid_rabot:
                f_vid_rabot = st.multiselect(
                    "Вид работ", options=all_vid_rabot,
                    default=[x for x in st.session_state.extra_filters.get('vid_rabot', []) if x in all_vid_rabot],
                    key="filter_vid_rabot_main"
                )
                st.session_state.extra_filters['vid_rabot'] = f_vid_rabot
        
        if 'ДОГОВОР' in df_for_options.columns:
            all_dogovor = sorted([x for x in df_for_options['ДОГОВОР'].unique() if x != 'Н/Д'])
            if all_dogovor and len(all_dogovor) < 500:
                f_dogovor = st.multiselect(
                    "Договор", options=all_dogovor,
                    default=[x for x in st.session_state.extra_filters.get('dogovor', []) if x in all_dogovor],
                    key="filter_dogovor_main"
                )
                st.session_state.extra_filters['dogovor'] = f_dogovor
    
    st.sidebar.divider()
    
    # ========================================
    # КНОПКА СБРОСА
    # ========================================
    if st.sidebar.button("🔄 Сбросить ВСЕ фильтры", use_container_width=True, key="reset_all_main"):
        reset_all_filters()
        # Очищаем pending
        if '_pending_hierarchy' in st.session_state:
            for level in HIERARCHY_LEVELS:
                st.session_state._pending_hierarchy[level['key']] = []
        st.rerun()
    
    return st.session_state.hierarchy_filters, st.session_state.extra_filters
