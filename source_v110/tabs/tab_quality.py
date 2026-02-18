# -*- coding: utf-8 -*-
"""
TAB 7: C4 КАЧЕСТВО ДАННЫХ
=========================
Проверяет ТОЛЬКО поля из справочника соответствия.
Пишет наименования человекочитаемым текстом.
НЕ обрезает список пустых полей.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

from utils.formatters import fmt
from utils.export import create_excel_download
from components.charts import CHART_FONT


# ============================================
# СПРАВОЧНИК: КОД ПОЛЯ -> НАИМЕНОВАНИЕ
# Из таблицы "Соответствие_поле-наименование"
# ============================================
FIELD_MAPPING = {
    'BUKRS': 'Балансовая единица',
    'AUFNR': 'Номер заказа',
    'ISTAT_TXT': 'Статус',
    'ERDAT': 'Время: начало',
    'AEDAT': 'Время: конец',
    'ERNAM': 'ФИО: начало',
    'AENAM': 'ФИО: конец',
    'BAUTL': 'Монтажный узел',
    'MSGRP': 'Помещение',
    'USER4': 'ПредваритЗатраты',
    'GSTRP': 'Базисный срок начала',
    'GLTRP': 'Базисный срок конца',
    'ZZFACTBEG': 'ZZFACTBEG',
    'ZZFACTEND': 'ZZFACTEND',
    'ZZ_DEFNUM': 'Номер дефектной ведомости',
    'ZZ_DOGNUM': 'Номер договора',
    'MAUFNR': 'Вышестоящий заказ',
    'AUART_TXT': 'Вид заказа',
    'INBDT': 'Дата ввода в эксплуатацию',
    'EQUNR_TXT': 'Единица оборудования',
    'IWERK_TXT': 'Планирующий завод',
    'GEWRK_TXT': 'Рабочее место',
    'ILART_TXT': 'Вид работы ТОРО',
    'STORT_TXT': 'Местоположение',
    'TPLNR8_TXT': 'Установка',
    'ABCKZ': 'Код ABC',
    'PMCOALLP': 'Плановые затраты',
    'PMCOALLF': 'Фактические затраты',
    'PMCO001P': 'Плановые трудозатраты',
    'PMCO001F': 'Фактические трудозатраты',
    'PMCO008P': 'План - МТР',
    'PMCO008F': 'Факт - МТР',
    'INGPR_TXT': 'Группа плановиков',
    'TPLNR_TXT': 'Техническое место',
    'CLINT_TXT': 'Класс',
}

# Маппинг переименованных колонок -> оригинальные SAP коды
RENAMED_TO_ORIGINAL = {
    'ID': 'AUFNR',
    'Текст': 'AUFNR_TXT',
    'БЕ': 'BUKRS',
    'STAT': 'ISTAT_TXT',
    'Вид': 'AUART_TXT',
    'ЕО': 'EQUNR_TXT',
    'ЗАВОД': 'IWERK_TXT',
    'РМ': 'GEWRK_TXT',
    'ВИД_РАБОТ': 'ILART_TXT',
    'МЕСТОПОЛ': 'STORT_TXT',
    'УСТАНОВКА': 'TPLNR8_TXT',
    'ABC': 'ABCKZ',
    'INGRP': 'INGPR_TXT',
    'ТМ': 'TPLNR_TXT',
    'КЛАСС': 'CLINT_TXT',
    'Plan_N': 'PMCOALLP',
    'Fact_N': 'PMCOALLF',
    'Plan_T': 'PMCO001P',
    'Fact_T': 'PMCO001F',
    'Начало': 'GSTRP',
    'Конец': 'GLTRP',
    'Факт_Начало': 'ZZFACTBEG',
    'Факт_Конец': 'ZZFACTEND',
    'ДОГОВОР': 'ZZ_DOGNUM',
    'ДЕФЕКТ_ВЕД': 'ZZ_DEFNUM',
    'USER': 'ERNAM',
    'MAUFNR': 'MAUFNR',
}

# Значения которые считаем "пустыми"
EMPTY_VALUES = {
    'Н/Д', 'н/д', 'N/A', 'n/a', 'NA', 'na',
    'nan', 'NaN', 'NAN', 'None', 'none', 'NONE',
    '', ' ', '  ', '0', '0.0',
    'Не присвоено', 'Не присв', 'не присвоено', 'не присв',
    'Пусто', 'пусто', 'ПУСТО',
    '-', '--', '—', '–',
    'null', 'NULL', 'Null',
    '#', '##', '###'
}


def _get_display_name(col_name: str) -> str:
    """Получить человекочитаемое наименование поля."""
    # Прямое соответствие (оригинальный SAP код)
    if col_name in FIELD_MAPPING:
        return FIELD_MAPPING[col_name]
    
    # Переименованная колонка -> ищем оригинал
    if col_name in RENAMED_TO_ORIGINAL:
        original = RENAMED_TO_ORIGINAL[col_name]
        if original in FIELD_MAPPING:
            return FIELD_MAPPING[original]
    
    return col_name


def _is_empty(val) -> bool:
    """Проверка: является ли значение пустым."""
    if val is None:
        return True
    if pd.isna(val):
        return True
    
    # Даты 1970/1971 = пустые
    if hasattr(val, 'year'):
        try:
            if val.year <= 1971:
                return True
            return False
        except:
            return True
    
    # Строки
    str_val = str(val).strip()
    if str_val in EMPTY_VALUES:
        return True
    if len(str_val) == 0:
        return True
    
    return False


def _find_columns_to_check(df_columns: list) -> dict:
    """
    Найти колонки для проверки.
    Возвращает dict: {колонка_в_df: наименование_из_справочника}
    """
    result = {}
    
    for col in df_columns:
        # 1. Прямое соответствие SAP коду
        if col in FIELD_MAPPING:
            result[col] = FIELD_MAPPING[col]
        # 2. Переименованная колонка
        elif col in RENAMED_TO_ORIGINAL:
            original = RENAMED_TO_ORIGINAL[col]
            if original in FIELD_MAPPING:
                result[col] = FIELD_MAPPING[original]
    
    return result


def render_tab_quality(df_f: pd.DataFrame) -> None:
    """Отрисовка вкладки C4 Качество данных."""
    
    st.subheader("▣ C4: Анализ качества данных")
    st.markdown(
        '<div class="dash-description">📊 <b>Качество данных (C4)</b> — '
        'проверка полноты заполнения полей из справочника (35 полей). '
        'Даты 1970 года = пустые.</div>',
        unsafe_allow_html=True
    )
    
    # ========================================
    # КОЛОНКИ ДЛЯ ПРОВЕРКИ (только из справочника)
    # ========================================
    columns_map = _find_columns_to_check(df_f.columns.tolist())
    total_rows = len(df_f)
    
    if len(columns_map) == 0:
        st.warning("Не найдено полей из справочника для проверки")
        return
    
    # ========================================
    # ПОДСЧЁТ ПУСТЫХ ПО КАЖДОМУ ПОЛЮ
    # ========================================
    empty_counts = []
    
    for col, display_name in columns_map.items():
        series = df_f[col]
        empty_cnt = sum(1 for val in series if _is_empty(val))
        pct = empty_cnt / total_rows * 100 if total_rows > 0 else 0
        
        empty_counts.append({
            'Колонка': col,
            'Наименование': display_name,
            'Незаполнено': empty_cnt,
            'Процент': pct
        })
    
    empty_df = pd.DataFrame(empty_counts).sort_values('Незаполнено', ascending=False)
    
    # ========================================
    # KPI
    # ========================================
    total_empty = empty_df['Незаполнено'].sum()
    total_cells = total_rows * len(columns_map)
    fill_rate = ((total_cells - total_empty) / total_cells * 100) if total_cells > 0 else 0
    problem_cols = len(empty_df[empty_df['Процент'] > 30])
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("ЗАКАЗОВ", fmt(total_rows))
    k2.metric("ПОЛЕЙ", fmt(len(columns_map)))
    k3.metric("ПРОБЛЕМНЫХ (>30%)", fmt(problem_cols))
    k4.metric("ЗАПОЛНЕННОСТЬ", f"{fill_rate:.1f}%")
    
    st.markdown("---")
    
    # ========================================
    # ФИЛЬТР
    # ========================================
    col_filter = st.radio(
        "Показать:",
        ["Все поля", "С пустыми (>0%)", "Проблемные (>30%)"],
        horizontal=True,
        key="col_filter_c4"
    )
    
    if col_filter == "С пустыми (>0%)":
        show_df = empty_df[empty_df['Незаполнено'] > 0]
    elif col_filter == "Проблемные (>30%)":
        show_df = empty_df[empty_df['Процент'] > 30]
    else:
        show_df = empty_df
    
    st.info(f"📊 Показано **{len(show_df)}** из {len(columns_map)} полей")
    
    # ========================================
    # ГРАФИК (по наименованиям)
    # ========================================
    st.markdown("### ▣ Незаполненность по полям")
    
    top30 = show_df.head(30)
    
    if len(top30) > 0:
        colors = ['#ff0055' if p > 30 else '#ffd700' if p > 10 else '#00f5d4' 
                  for p in top30['Процент']]
        
        fig = go.Figure(go.Bar(
            y=top30['Наименование'].astype(str),
            x=top30['Незаполнено'],
            orientation='h',
            marker=dict(color=colors, line=dict(color='#ffffff', width=1)),
            text=[f"{fmt(c)} ({p:.1f}%)" for c, p in zip(top30['Незаполнено'], top30['Процент'])],
            textposition='outside',
            textfont=dict(color='#ffffff', size=11)
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=CHART_FONT,
            height=max(400, len(top30) * 28),
            yaxis=dict(categoryorder='total ascending'),
            margin=dict(l=250, r=100)
        )
        
        st.plotly_chart(fig, use_container_width=True, key="chart_c4")
    
    st.markdown("""
    <div style="display:flex; gap:20px; margin:10px 0;">
        <span style="color:#ff0055;">🔴 >30%</span>
        <span style="color:#ffd700;">🟡 10-30%</span>
        <span style="color:#00f5d4;">🟢 <10%</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================
    # ТАБЛИЦА ПОЛЕЙ
    # ========================================
    st.markdown("### ▣ Детализация по полям")
    
    tbl = show_df.copy()
    tbl['Заполнено'] = total_rows - tbl['Незаполнено']
    tbl['Процент'] = tbl['Процент'].round(1)
    tbl = tbl[['Наименование', 'Колонка', 'Заполнено', 'Незаполнено', 'Процент']]
    tbl.columns = ['Наименование', 'Код поля', 'Заполнено', 'Пусто', '% пустых']
    
    st.dataframe(tbl, use_container_width=True, hide_index=True, height=400)
    
    excel_cols = create_excel_download(tbl, "c4_fields")
    st.download_button(
        "📥 Excel (по полям)",
        data=excel_cols,
        file_name=f"c4_fields_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_c4_cols"
    )
    
    st.markdown("---")
    
    # ========================================
    # ЗАКАЗЫ С ПУСТЫМИ ПОЛЯМИ
    # ========================================
    st.markdown("### ▣ Заказы с незаполненными полями")
    
    def count_empty(row):
        """Считает кол-во пустых полей."""
        return sum(1 for col in columns_map.keys() if _is_empty(row.get(col)))
    
    def list_empty_names(row):
        """
        Возвращает ВСЕ незаполненные поля НАИМЕНОВАНИЯМИ (не кодами).
        БЕЗ обрезки "+24".
        """
        empty_names = []
        for col, display_name in columns_map.items():
            if _is_empty(row.get(col)):
                empty_names.append(display_name)
        return ', '.join(empty_names) if empty_names else '—'
    
    df_f['_N_empty'] = df_f.apply(count_empty, axis=1)
    df_f['_Empty_names'] = df_f.apply(list_empty_names, axis=1)
    
    max_empty = int(df_f['_N_empty'].max()) if len(df_f) > 0 else 1
    threshold = st.slider(
        "Показать заказы с кол-вом пустых полей ≥",
        min_value=1, max_value=max(max_empty, 1), value=min(5, max_empty),
        key="threshold_c4"
    )
    
    bad_orders = df_f[df_f['_N_empty'] >= threshold].copy()
    
    st.info(f"📊 **{len(bad_orders)}** заказов с ≥{threshold} пустых полей")
    
    if len(bad_orders) > 0:
        # Колонки для отображения
        cols_show = ['ID', 'Текст', 'ТМ', 'Вид', '_N_empty', '_Empty_names']
        cols_exist = [c for c in cols_show if c in bad_orders.columns]
        
        display_df = bad_orders[cols_exist].sort_values('_N_empty', ascending=False).head(200).copy()
        display_df.columns = [
            c.replace('_N_empty', 'Пустых полей').replace('_Empty_names', 'Незаполненные поля') 
            for c in cols_exist
        ]
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=450)
        
        # Excel - ВСЕ заказы, ВСЕ поля полностью (без обрезки)
        export_df = bad_orders[cols_exist].sort_values('_N_empty', ascending=False).copy()
        export_df.columns = [
            c.replace('_N_empty', 'Пустых полей').replace('_Empty_names', 'Незаполненные поля') 
            for c in cols_exist
        ]
        
        excel_orders = create_excel_download(export_df, "c4_orders")
        st.download_button(
            "📥 Excel (по заказам)",
            data=excel_orders,
            file_name=f"c4_orders_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_c4_orders"
        )
    else:
        st.success(f"✓ Нет заказов с ≥{threshold} пустых полей")
    
    df_f.drop(['_N_empty', '_Empty_names'], axis=1, inplace=True, errors='ignore')
