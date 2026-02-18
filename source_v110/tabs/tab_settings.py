# -*- coding: utf-8 -*-
"""
tabs/tab_settings.py — TAB 9: НАСТРОЙКИ СТИЛЕЙ

ИЗМЕНЕНИЯ v111.1:
- БЕЗ st.rerun() при каждом изменении слайдера — мгновенное применение
- 6 цветовых схем + размер шрифтов
"""

import streamlit as st
import json
import plotly.graph_objects as go
from datetime import datetime


# ============================================
# ДЕФОЛТНАЯ ТЕМА
# ============================================
DEFAULT_THEME = {
    "colors": {
        "background": "#020408",
        "sidebar_bg": "#020408",
        "card_bg": "#1a1a2e",
        "primary": "#00f5d4",
        "danger": "#ff0055",
        "warning": "#ffd700",
        "success": "#10b981",
        "purple": "#8b5cf6",
        "orange": "#ff6b35",
        "text": "#FFFFFF",
        "text_muted": "#888888",
        "border": "#00f5d4"
    },
    "fonts": {
        "family": "Arial, sans-serif",
        "size_base": 32,
        "size_header": 32,
        "size_metric": 42,
        "weight_bold": 700
    },
    "charts": {
        "height_small": 180,
        "height_medium": 400,
        "donut_hole": 0.7,
        "bar_line_width": 1
    },
    "layout": {
        "card_padding": 20,
        "card_radius": 8,
        "border_width": 2
    }
}

# ============================================
# 6 ЦВЕТОВЫХ СХЕМ
# ============================================
PRESETS = {
    "ТИТАН Original": DEFAULT_THEME,
    "Светлая": {
        "colors": {
            "background": "#f5f5f5",
            "sidebar_bg": "#ffffff",
            "card_bg": "#ffffff",
            "primary": "#0066cc",
            "danger": "#dc3545",
            "warning": "#ffc107",
            "success": "#28a745",
            "purple": "#6f42c1",
            "orange": "#fd7e14",
            "text": "#212529",
            "text_muted": "#6c757d",
            "border": "#0066cc"
        },
        "fonts": DEFAULT_THEME["fonts"].copy(),
        "charts": DEFAULT_THEME["charts"].copy(),
        "layout": DEFAULT_THEME["layout"].copy()
    },
    "Midnight Blue": {
        "colors": {
            "background": "#0a1929",
            "sidebar_bg": "#0a1929",
            "card_bg": "#132f4c",
            "primary": "#5090d3",
            "danger": "#f44336",
            "warning": "#ffb74d",
            "success": "#66bb6a",
            "purple": "#ab47bc",
            "orange": "#ff7043",
            "text": "#ffffff",
            "text_muted": "#b2bac2",
            "border": "#5090d3"
        },
        "fonts": DEFAULT_THEME["fonts"].copy(),
        "charts": DEFAULT_THEME["charts"].copy(),
        "layout": DEFAULT_THEME["layout"].copy()
    },
    "Терминал": {
        "colors": {
            "background": "#0d0d0d",
            "sidebar_bg": "#0d0d0d",
            "card_bg": "#1a1a1a",
            "primary": "#00ff00",
            "danger": "#ff3333",
            "warning": "#ffff00",
            "success": "#00ff00",
            "purple": "#ff00ff",
            "orange": "#ff9900",
            "text": "#00ff00",
            "text_muted": "#008800",
            "border": "#00ff00"
        },
        "fonts": {
            "family": "Consolas, monospace",
            "size_base": 14,
            "size_header": 24,
            "size_metric": 32,
            "weight_bold": 700
        },
        "charts": DEFAULT_THEME["charts"].copy(),
        "layout": DEFAULT_THEME["layout"].copy()
    },
    "Роза": {
        "colors": {
            "background": "#1a0a14",
            "sidebar_bg": "#1a0a14",
            "card_bg": "#2d1f2a",
            "primary": "#ff6b9d",
            "danger": "#ff4757",
            "warning": "#feca57",
            "success": "#1dd1a1",
            "purple": "#c56cf0",
            "orange": "#ff9f43",
            "text": "#ffffff",
            "text_muted": "#a0a0a0",
            "border": "#ff6b9d"
        },
        "fonts": DEFAULT_THEME["fonts"].copy(),
        "charts": DEFAULT_THEME["charts"].copy(),
        "layout": DEFAULT_THEME["layout"].copy()
    },
    "Индустриальная": {
        "colors": {
            "background": "#1a1a1a",
            "sidebar_bg": "#1a1a1a",
            "card_bg": "#2d2d2d",
            "primary": "#f59e0b",
            "danger": "#ef4444",
            "warning": "#f59e0b",
            "success": "#22c55e",
            "purple": "#a855f7",
            "orange": "#f97316",
            "text": "#e5e5e5",
            "text_muted": "#737373",
            "border": "#f59e0b"
        },
        "fonts": DEFAULT_THEME["fonts"].copy(),
        "charts": DEFAULT_THEME["charts"].copy(),
        "layout": DEFAULT_THEME["layout"].copy()
    }
}


def init_theme_state():
    """Инициализация темы в session_state."""
    if 'theme' not in st.session_state:
        st.session_state.theme = json.loads(json.dumps(DEFAULT_THEME))
    if 'theme_history' not in st.session_state:
        st.session_state.theme_history = []


def save_to_history():
    """Сохранить текущее состояние в историю."""
    st.session_state.theme_history.append(json.dumps(st.session_state.theme))
    if len(st.session_state.theme_history) > 20:
        st.session_state.theme_history.pop(0)


def generate_styles(theme=None):
    """Генерация CSS из темы."""
    if theme is None:
        if 'theme' not in st.session_state:
            theme = DEFAULT_THEME
        else:
            theme = st.session_state.theme
    
    c = theme['colors']
    f = theme['fonts']
    lo = theme['layout']
    
    return f'''
<style>
    /* ========== ОСНОВА ========== */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .stApp {{
        background-color: {c['background']} !important; 
        color: {c['text']} !important;
        font-family: {f['family']};
        font-size: {f['size_base']}px !important;
    }}
    
    /* ========== ГЛОБАЛЬНЫЕ ШРИФТЫ ========== */
    .stApp p, .stApp div, .stApp span, .stApp li, .stApp td, .stApp th, 
    .stApp label, .stApp .stMarkdown, .stApp .stText,
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] div,
    [data-testid="stAppViewContainer"] span {{
        font-size: {f['size_base']}px !important;
    }}
    .stApp h1, [data-testid="stAppViewContainer"] h1 {{ font-size: {f['size_header'] + 12}px !important; }}
    .stApp h2, [data-testid="stAppViewContainer"] h2 {{ font-size: {f['size_header'] + 6}px !important; }}
    .stApp h3, [data-testid="stAppViewContainer"] h3 {{ font-size: {f['size_header']}px !important; }}
    .stApp h4, [data-testid="stAppViewContainer"] h4 {{ font-size: {f['size_header'] - 4}px !important; }}
    
    /* Вкладки — названия */
    .stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] span {{
        font-size: {f['size_base']}px !important;
    }}
    
    /* Dataframe */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th,
    .stDataFrame td, .stDataFrame th {{
        font-size: {max(f['size_base'] - 1, 11)}px !important;
    }}
    
    /* Подписи */
    .stApp .stCaption, [data-testid="stCaptionContainer"] p {{
        font-size: {max(f['size_base'] - 2, 10)}px !important;
    }}
    
    /* Expander */
    [data-testid="stExpander"] summary span p {{
        font-size: {f['size_base'] + 1}px !important;
    }}
    
    /* Selectbox, multiselect, radio */
    .stApp .stSelectbox label p, .stApp .stMultiSelect label p, .stApp .stRadio label p {{
        font-size: {f['size_base']}px !important;
    }}
    .stApp [data-baseweb="select"] span {{
        font-size: {f['size_base']}px !important;
    }}
    
    /* Plotly chart текст — не трогаем, у Plotly свой font */
    
    /* ========== САЙДБАР ========== */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
        background-color: {c['sidebar_bg']} !important; 
        border-right: {lo['border_width']}px solid {c['border']} !important;
    }}
    
    /* ========== КНОПКИ ========== */
    button, [data-testid="stFileUploader"] button {{
        background-color: {c['background']} !important; 
        color: {c['primary']} !important;
        border: {lo['border_width']}px solid {c['primary']} !important; 
        font-weight: {f['weight_bold']} !important;
        text-transform: uppercase !important; 
        border-radius: {lo['card_radius']//2}px !important;
    }}
    button:hover {{ 
        background-color: {c['primary']} !important; 
        color: {c['background']} !important;
        box-shadow: 0 0 15px {c['primary']}99 !important;
    }}
    
    /* ========== ИНПУТЫ ========== */
    div[data-baseweb="select"], .stSelectbox div[role="button"], 
    div[data-baseweb="input"], .stTextInput input {{
        background-color: {c['card_bg']} !important; 
        border: none !important;
        border-bottom: {lo['border_width']}px solid {c['primary']} !important; 
        color: {c['text']} !important;
    }}
    
    /* ========== МЕТРИКИ ========== */
    [data-testid="stMetricValue"] {{ 
        color: {c['text']} !important; 
        font-weight: {f['weight_bold']}; 
        font-size: {f['size_metric']}px !important; 
    }}
    [data-testid="stMetricLabel"] {{ 
        color: {c['primary']} !important; 
        font-weight: {f['weight_bold']}; 
        font-size: {f['size_base'] - 2}px !important;
    }}
    
    /* ========== ПРОГРЕСС-БАР ========== */
    .stProgress > div > div > div > div {{
        background-color: {c['primary']} !important;
    }}
    
    /* ========== ВКЛАДКИ ========== */
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {c['background']};
        border: {lo['border_width']}px solid {c['primary']};
        color: {c['primary']};
        font-weight: {f['weight_bold']};
        padding: 10px 20px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {c['primary']} !important;
        color: {c['background']} !important;
    }}
    
    /* ========== КАРТОЧКИ ========== */
    .method-card {{
        background: linear-gradient(135deg, {c['background']} 0%, {c['card_bg']} 100%);
        border-left: 5px solid {c['primary']};
        padding: {lo['card_padding']}px;
        border-radius: {lo['card_radius']}px;
        margin: 10px 0;
        box-shadow: 0 4px 6px {c['primary']}1a;
    }}
    .risk-card {{
        background: linear-gradient(135deg, {c['card_bg']} 0%, #2d1f3d 100%);
        border-left: 5px solid {c['danger']};
        padding: {lo['card_padding'] - 2}px;
        border-radius: {lo['card_radius']}px;
        margin: 8px 0;
    }}
    .info-box {{
        background: linear-gradient(135deg, {c['background']} 0%, {c['card_bg']} 100%);
        border: 1px solid {c['primary']};
        border-radius: {lo['card_radius']}px;
        padding: {lo['card_padding'] - 5}px;
        margin: 10px 0;
    }}
    .max-order-card {{
        background: linear-gradient(135deg, {c['card_bg']} 0%, {c['background']} 100%);
        border-radius: {lo['card_radius']}px;
        padding: 10px 15px;
        margin: 5px 0;
        border-left: 4px solid;
    }}
    
    /* ========== ОПИСАНИЯ ========== */
    .dash-description {{
        background: linear-gradient(135deg, {c['background']} 0%, {c['card_bg']} 100%);
        border-left: 4px solid {c['primary']};
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0 16px 0;
        color: {c['text_muted']};
        font-size: {f['size_base'] - 1}px;
    }}
    .analytics-hint {{
        background: linear-gradient(135deg, {c['card_bg']} 0%, {c['background']} 100%);
        border-left: 4px solid {c['warning']};
        border-radius: 6px;
        padding: 10px 14px;
        margin: 8px 0;
        color: #aaa;
        font-size: {f['size_base'] - 2}px;
    }}
    
    /* ========== НАВИГАЦИЯ ========== */
    .breadcrumb {{
        background: linear-gradient(135deg, #0a1628 0%, #1a2942 100%);
        border: 1px solid {c['primary']};
        border-radius: {lo['card_radius']}px;
        padding: 12px 20px;
        margin: 10px 0;
        font-size: {f['size_base'] + 2}px;
        color: {c['primary']};
    }}
    
    /* ========== ФИЛЬТРЫ ========== */
    .filter-section {{
        background: linear-gradient(135deg, {c['background']} 0%, {c['card_bg']} 100%);
        border: 1px solid #1e3a5f;
        border-radius: {lo['card_radius']}px;
        padding: 12px;
        margin: 8px 0;
    }}
    .planner-card {{
        background: linear-gradient(135deg, #0a1628 0%, #1a2942 100%);
        border: 1px solid {c['primary']};
        border-radius: {lo['card_radius']}px;
        padding: 15px;
        margin: 8px 0;
    }}
    .rm-card {{
        background: linear-gradient(135deg, #1a1628 0%, #2a1942 100%);
        border: 1px solid {c['danger']};
        border-radius: {lo['card_radius']}px;
        padding: 15px;
        margin: 8px 0;
    }}
    .no-data-badge {{
        background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
        border: 1px dashed #666;
        border-radius: {lo['card_radius']}px;
        padding: 15px;
        margin: 10px 0;
        color: {c['text_muted']};
        text-align: center;
    }}
    .clickable-card {{
        cursor: pointer;
        transition: all 0.2s ease;
    }}
    .clickable-card:hover {{
        transform: scale(1.02);
        box-shadow: 0 0 20px {c['primary']}4d;
    }}
</style>
'''


def render_tab_settings():
    """Отрисовка вкладки НАСТРОЙКИ (v111.1 — без rerun на слайдерах)."""
    
    init_theme_state()
    
    st.subheader("⚙️ Настройки стилей")
    st.markdown(
        '<div class="dash-description">🎨 <b>Настройки</b> — '
        'выберите цветовую схему и настройте размер шрифтов.</div>',
        unsafe_allow_html=True
    )
    
    # ========================================
    # 6 ЦВЕТОВЫХ СХЕМ
    # ========================================
    st.markdown("### 🎭 Цветовая схема")
    
    preset_cols = st.columns(len(PRESETS))
    
    for i, (preset_name, preset_theme) in enumerate(PRESETS.items()):
        with preset_cols[i]:
            c = preset_theme['colors']
            st.markdown(
                f'<div style="background:{c["background"]}; border:2px solid {c["primary"]}; '
                f'border-radius:8px; padding:8px; text-align:center; margin-bottom:4px;">'
                f'<span style="color:{c["primary"]}; font-weight:bold;">●</span> '
                f'<span style="color:{c["danger"]};">●</span> '
                f'<span style="color:{c["warning"]};">●</span> '
                f'<span style="color:{c["success"]};">●</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(preset_name, use_container_width=True, key=f"preset_{i}"):
                save_to_history()
                st.session_state.theme = json.loads(json.dumps(preset_theme))
                st.rerun()
    
    st.markdown("---")
    
    # ========================================
    # НАСТРОЙКА ШРИФТОВ (без rerun — применяется при следующем действии)
    # ========================================
    st.markdown("### 🔤 Размер шрифтов")
    
    f = st.session_state.theme['fonts']
    
    with st.form(key="font_settings_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_base = st.slider(
                "Базовый размер", 10, 24, f['size_base'],
                help="Основной размер текста", key="f_base"
            )
        
        with col2:
            new_metric = st.slider(
                "Размер метрик", 24, 56, f['size_metric'],
                help="Размер KPI-чисел", key="f_metric"
            )
        
        with col3:
            new_header = st.slider(
                "Размер заголовков", 18, 42, f['size_header'],
                help="Размер заголовков секций", key="f_header"
            )
        
        col_a1, col_a2, col_a3, _ = st.columns([1, 1, 1, 3])
        
        with col_a1:
            apply_fonts = st.form_submit_button("✅ Применить шрифты", type="primary")
        with col_a2:
            reset_fonts = st.form_submit_button("🔄 Сброс по умолчанию")
    
    if apply_fonts:
        save_to_history()
        st.session_state.theme['fonts']['size_base'] = new_base
        st.session_state.theme['fonts']['size_metric'] = new_metric
        st.session_state.theme['fonts']['size_header'] = new_header
        st.rerun()
    
    if reset_fonts:
        save_to_history()
        st.session_state.theme['fonts'] = json.loads(json.dumps(DEFAULT_THEME['fonts']))
        st.rerun()
    
    # Отменить (вне формы — одна кнопка)
    if st.button("↩️ Отменить последнее", disabled=len(st.session_state.theme_history) == 0, key="undo_theme"):
        st.session_state.theme = json.loads(st.session_state.theme_history.pop())
        st.rerun()
    
    st.markdown("---")
    
    # ========================================
    # ПРЕВЬЮ
    # ========================================
    st.markdown("### 👁 Превью текущей темы")
    
    c = st.session_state.theme['colors']
    f = st.session_state.theme['fonts']
    ch = st.session_state.theme['charts']
    
    st.markdown(f'<div class="breadcrumb">🔍 БЕ: 1000 → Завод: Томск → Установка: ST01</div>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Заказов", "1 234")
    m2.metric("План", "45.6М ₽")
    m3.metric("Факт", "52.3М ₽", delta="+14.6%", delta_color="inverse")
    m4.metric("С риском", "187")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(f'''
        <div class="method-card">
            <span style="color:{c['primary']}; font-size:20px; font-weight:bold;">▲ C1-M1</span><br>
            <span style="color:{c['text_muted']};">Перерасход бюджета</span><br><br>
            <span style="color:{c['danger']}; font-size:24px; font-weight:bold;">47</span>
            <span style="color:{c['text_muted']};"> срабатываний</span>
        </div>
        ''', unsafe_allow_html=True)
    with col_c2:
        st.markdown(f'''
        <div class="risk-card">
            <span style="color:{c['danger']}; font-size:20px; font-weight:bold;">⚠ РИСК</span><br>
            <span style="color:{c['text_muted']};">Проблемное оборудование</span><br><br>
            <span style="color:{c['warning']}; font-size:24px; font-weight:bold;">23</span>
            <span style="color:{c['text_muted']};"> единицы</span>
        </div>
        ''', unsafe_allow_html=True)
