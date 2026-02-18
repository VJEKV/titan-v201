# -*- coding: utf-8 -*-
"""
ТИТАН Аудит ТОРО v.110
======================
Система анализа заказов ТОРО с 7 вкладками и 6 методами риск-скоринга.

ТОЧКА ВХОДА:
-----------
streamlit run app.py

СТРУКТУРА ПРОЕКТА:
-----------------
toro_modules/
├── app.py              <- ВЫ ЗДЕСЬ (главный файл)
├── config/             <- Конфигурация (стили, константы, настройки)
├── core/               <- Ядро обработки данных
├── components/         <- UI компоненты (sidebar, KPI, графики)
├── tabs/               <- 7 вкладок дашборда
├── utils/              <- Утилиты (форматирование, парсинг, экспорт)
└── STRUCTURE.md        <- Карта проекта

АВТОР: Евгений (ТИТАН Аудит ТОРО)
ВЕРСИЯ: 110 (модульная архитектура)
"""

import streamlit as st
import time
from datetime import datetime

# ============================================
# ИМПОРТЫ ИЗ МОДУЛЕЙ ПРОЕКТА
# ============================================
import pandas as pd

# Конфигурация
from config.styles import STYLES
from config.settings import init_session_state

# Динамические стили
from tabs.tab_settings import generate_styles, init_theme_state

# Ядро обработки данных
from core.data_loader import load_file, detect_export_format
from core.data_processor import process_data
from core.aggregates import compute_aggregates
from core.risk_scoring import apply_risk_scoring

# UI компоненты
from components.sidebar import render_sidebar
from components.kpi_block import render_kpi, calculate_level_kpi

# Утилиты
from utils.filters import apply_hierarchy_filters, build_breadcrumb
from utils.formatters import fmt

# Вкладки
from tabs import (
    render_tab_finance,
    render_tab_timeline,
    render_tab_work_types,
    render_tab_planners,
    render_tab_workplaces,
    render_tab_risks,
    render_tab_quality
)
from tabs.tab_orders import render_tab_orders


# ============================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ============================================
st.set_page_config(
    page_title="ТИТАН Аудит ТОРО v.110",
    layout="wide",
    page_icon="⚙️"
)

# ============================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================
init_session_state()
init_theme_state()

# Применяем стили (динамические из темы или статические)
if 'theme' in st.session_state:
    st.markdown(generate_styles(st.session_state.theme), unsafe_allow_html=True)
else:
    st.markdown(STYLES, unsafe_allow_html=True)

# Жёсткое управление шрифтами через S/M/L
_fs_map = {'S': (13, 28, 11), 'M': (16, 36, 14), 'L': (20, 44, 17)}
_fs_base, _fs_metric, _fs_label = _fs_map.get(st.session_state.get('font_size', 'M'), _fs_map['M'])
st.markdown(f"""<style>
    /* Названия вкладок */
    button[data-baseweb="tab"] {{
        font-size: {_fs_base + 2}px !important;
    }}
    button[data-baseweb="tab"] p {{
        font-size: {_fs_base + 2}px !important;
    }}
    button[data-baseweb="tab"] div {{
        font-size: {_fs_base + 2}px !important;
    }}
    [data-baseweb="tab-list"] button {{
        font-size: {_fs_base + 2}px !important;
        padding: 12px 24px !important;
    }}
</style>""", unsafe_allow_html=True)


# ============================================
# ЗАГОЛОВОК
# ============================================
st.title("⚙️ ТИТАН Аудит ТОРО v.112")
st.caption("9 вкладок • 6 методов риск-скоринга • Редактор стилей")


# ============================================
# ЗАГРУЗКА ФАЙЛА (SIDEBAR)
# ============================================
file = st.sidebar.file_uploader(
    "▣ ЗАГРУЗИТЬ ВЫГРУЗКУ SAP",
    type=["xlsx", "csv"],
    help="Поддерживаются оба формата: старый и новый (с историей статусов)"
)

if not file:
    st.markdown('<p style="font-size: 1.5rem; color: #00f5d4;">◂ Загрузите выгрузку SAP для начала работы</p>', unsafe_allow_html=True)
    st.stop()


# ============================================
# ОБРАБОТКА ДАННЫХ
# ============================================
start_time = time.time()

# Индикатор загрузки
progress_placeholder = st.empty()
with progress_placeholder.container():
    status_text = st.empty()
    progress_bar = st.progress(0)

# Шаг 1: Загрузка файла
status_text.text("▣ Загрузка файла...")
df_raw = load_file(file, file.name)
progress_bar.progress(25)

# Шаг 2: Обработка данных
status_text.text("▣ Парсинг данных...")
df = process_data(df_raw)

# ============================================
# ОПТИМИЗАЦИЯ ПАМЯТИ: object → category
# Предотвращает ArrayMemoryError при фильтрации
# pandas 2.x делает consolidate при каждом df[mask],
# 48 object-колонок вызывают numpy vstack crash
# ============================================
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].astype('category')

progress_bar.progress(50)

# Определяем формат выгрузки (для внутреннего использования)
export_format = df.attrs.get('export_format', 'LEGACY')

# Шаг 3: Агрегаты
status_text.text("▣ Вычисление агрегатов...")
agg = compute_aggregates(df)
progress_bar.progress(70)


# ============================================
# SIDEBAR: ФИЛЬТРЫ
# ============================================
render_sidebar(df)


# ============================================
# ПРИМЕНЕНИЕ ФИЛЬТРОВ
# ============================================
status_text.text("▣ Применение фильтров...")

# Иерархические фильтры — через .loc с индексами вместо df[mask]
idx = apply_hierarchy_filters(df, st.session_state.hierarchy_filters).index
mask = pd.Series(True, index=df.index)

# Дополнительные фильтры из extra_filters
ef = st.session_state.extra_filters

# Поиск по тексту
if ef.get('search'):
    search_lower = ef['search'].lower()
    mask = mask & (
        df['ID'].astype(str).str.lower().str.contains(search_lower, na=False) |
        df['Текст'].astype(str).str.lower().str.contains(search_lower, na=False)
    )

# Фильтр по виду заказа
if ef.get('vid_kod') and 'Вид_Код' in df.columns:
    mask = mask & df['Вид_Код'].isin(ef['vid_kod'])
elif ef.get('vid'):
    mask = mask & df['Вид'].isin(ef['vid'])

# Фильтр по ABC
if ef.get('abc'):
    mask = mask & df['ABC'].isin(ef['abc'])

# Фильтр по статусу
if ef.get('stat'):
    mask = mask & df['STAT'].isin(ef['stat'])

# Фильтр по классу оборудования
if ef.get('klass') and 'КЛАСС' in df.columns:
    mask = mask & df['КЛАСС'].isin(ef['klass'])

# Фильтр по рабочему месту
if ef.get('rm') and 'РМ' in df.columns:
    mask = mask & df['РМ'].isin(ef['rm'])

# Фильтр по группе плановиков
if ef.get('ingrp') and 'INGRP' in df.columns:
    mask = mask & df['INGRP'].isin(ef['ingrp'])

# Фильтр по виду работ
if ef.get('vid_rabot') and 'Вид' in df.columns:
    mask = mask & df['Вид'].isin(ef['vid_rabot'])

# Фильтр по договору
if ef.get('dogovor') and 'ДОГОВОР' in df.columns:
    mask = mask & df['ДОГОВОР'].isin(ef['dogovor'])

# Фильтр по дате
if ef.get('date_from') and ef.get('date_to') and 'Конец' in df.columns:
    mask = mask & (
        (df['Конец'].dt.date >= ef['date_from']) &
        (df['Конец'].dt.date <= ef['date_to'])
    )

# Применяем ВСЕ фильтры одной операцией — через .loc по индексу
final_idx = idx.intersection(df.index[mask])
df_filtered = df.loc[final_idx]

progress_bar.progress(85)


# ============================================
# РАСЧЁТ РИСКОВ
# ============================================
status_text.text("▣ Расчёт рисков...")

# Пересчитываем агрегаты на отфильтрованных данных
agg_filtered = compute_aggregates(df_filtered)

# Применяем риск-скоринг
df_f = apply_risk_scoring(
    df_filtered.copy(),
    agg_filtered,
    st.session_state.method_thresholds
)

progress_bar.progress(100)
total_time = time.time() - start_time
progress_placeholder.empty()


# ============================================
# ХЛЕБНЫЕ КРОШКИ
# ============================================
breadcrumb_text = build_breadcrumb(st.session_state.hierarchy_filters)
st.markdown(f'<div class="breadcrumb">🔍 {breadcrumb_text}</div>', unsafe_allow_html=True)


# ============================================
# ПОИСК ЗАКАЗОВ
# ============================================
st.markdown("## 🔍 ПОИСК ЗАКАЗОВ")

# Получаем список всех ID заказов
all_order_ids = df_f['ID'].unique().tolist()

# Мультиселект с тегами
selected_orders = st.multiselect(
    "Введите или выберите номера заказов:",
    options=all_order_ids,
    default=[],
    placeholder="Начните вводить номер заказа...",
    key="order_search_tags"
)

# Если выбраны заказы — показываем таблицу
if selected_orders:
    # Фильтруем по выбранным заказам
    df_search = df_f[df_f['ID'].isin(selected_orders)].copy()
    
    # Добавляем столбец Отклонение
    df_search['Отклонение'] = df_search['Fact_N'] - df_search['Plan_N']
    
    # Выбираем 20 столбцов
    columns_to_show = [
        'ID', 'Текст', 'ТМ', 'ЕО', 'Вид', 'STAT', 'ABC',
        'Plan_N', 'Fact_N', 'Отклонение', 'Начало', 'Конец',
        'INGRP', 'USER', 'РМ', 'Risk_Sum', 'ЗАВОД', 'УСТАНОВКА', 'БЕ', 'Data_Completeness'
    ]
    
    # Оставляем только существующие столбцы
    columns_exist = [c for c in columns_to_show if c in df_search.columns]
    df_display = df_search[columns_exist].copy()
    
    # Показываем количество найденных
    st.success(f"✅ Найдено заказов: {len(df_display)}")
    
    # Таблица
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Кнопка выгрузки в Excel
    from utils.export import create_excel_download
    excel_search = create_excel_download(df_display, "search_orders")
    st.download_button(
        "📥 ВЫГРУЗИТЬ В EXCEL",
        data=excel_search,
        file_name=f"orders_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_search_orders"
    )
else:
    st.info("👆 Выберите номера заказов для отображения")

st.markdown("---")


# ============================================
# KPI БЛОК
# ============================================
kpi = calculate_level_kpi(df_f)
render_kpi(df_f, kpi)


# ============================================
# 9 ВКЛАДОК DASHBOARD
# ============================================
st.markdown("## ▤ АНАЛИТИЧЕСКИЙ DASHBOARD")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "▣ ФИНАНСЫ",
    "▣ СРОКИ", 
    "▣ ВИДЫ РАБОТ",
    "▣ ПЛАНОВИКИ",
    "▣ РАБ.МЕСТА",
    "▣ РИСКИ",
    "▣ C4 КАЧЕСТВО",
    "▣ ЗАКАЗЫ",
])

with tab1:
    render_tab_finance(df_f)

with tab2:
    render_tab_timeline(df_f)

with tab3:
    render_tab_work_types(df_f)

with tab4:
    render_tab_planners(df_f)

with tab5:
    render_tab_workplaces(df_f)

with tab6:
    render_tab_risks(df_f, agg_filtered, st.session_state.method_thresholds)

with tab7:
    render_tab_quality(df_f)

with tab8:
    render_tab_orders(df_f)


# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption(
    f"⚙️ ТИТАН Аудит ТОРО v.112 | "
    f"{total_time:.1f} сек | "
    f"{fmt(len(df_f))} строк | "
    f"Шрифт: {st.session_state.get('font_size', 'M')} | "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
