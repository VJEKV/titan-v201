# -*- coding: utf-8 -*-
"""
config/styles.py — CSS стили INDUSTRIAL SUPREME

Тёмная тема с акцентами #00f5d4 (бирюзовый) и #ff0055 (красный).
"""

STYLES = """
<style>
    /* ========== ОСНОВА ========== */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .stApp {
        background-color: #020408 !important; 
        color: #FFFFFF !important;
    }
    
    /* ========== САЙДБАР ========== */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #020408 !important; 
        border-right: 2px solid #00f5d4 !important;
    }
    
    /* ========== КНОПКИ ========== */
    button, [data-testid="stFileUploader"] button {
        background-color: #0a0a0a !important; 
        color: #00f5d4 !important;
        border: 2px solid #00f5d4 !important; 
        font-weight: 900 !important;
        text-transform: uppercase !important; 
        border-radius: 4px !important;
    }
    button:hover { 
        background-color: #00f5d4 !important; 
        color: #020408 !important;
        box-shadow: 0 0 15px rgba(0,245,212,0.6) !important;
    }
    
    /* ========== ИНПУТЫ ========== */
    div[data-baseweb="select"], .stSelectbox div[role="button"], 
    div[data-baseweb="input"], .stTextInput input {
        background-color: #11141c !important; 
        border: none !important;
        border-bottom: 2px solid #00f5d4 !important; 
        color: #FFFFFF !important;
    }
    
    /* ========== МЕТРИКИ ========== */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-weight: 900; 
        font-size: 2.0rem !important; 
    }
    [data-testid="stMetricLabel"] { 
        color: #00f5d4 !important; 
        font-weight: 700; 
        font-size: 2.0rem !important;
    }
    
    /* ========== ПРОГРЕСС-БАР ========== */
    .stProgress > div > div > div > div {
        background-color: #00f5d4 !important;
    }
    
    /* ========== ВКЛАДКИ ========== */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #0a0a0a;
        border: 2px solid #00f5d4;
        color: #00f5d4;
        font-weight: 800;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00f5d4 !important;
        color: #020408 !important;
    }
    
    /* ========== КАРТОЧКИ ========== */
    .method-card {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        border-left: 5px solid #00f5d4;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,245,212,0.1);
    }
    
    .risk-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #2d1f3d 100%);
        border-left: 5px solid #ff0055;
        padding: 18px;
        border-radius: 8px;
        margin: 8px 0;
    }
    
    .info-box {
        background: linear-gradient(135deg, #0a0f1a 0%, #1a1a2e 100%);
        border: 1px solid #00f5d4;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .max-order-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #0d1117 100%);
        border-radius: 8px;
        padding: 10px 15px;
        margin: 5px 0;
        border-left: 4px solid;
    }
    
    /* ========== ОПИСАНИЯ ========== */
    .dash-description {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        border-left: 4px solid #00f5d4;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0 16px 0;
        color: #8b949e;
        font-size: 0.95rem;
    }
    
    .analytics-hint {
        background: linear-gradient(135deg, #1a1a2e 0%, #0d1117 100%);
        border-left: 4px solid #ffd700;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 8px 0;
        color: #aaa;
        font-size: 0.9rem;
    }
    
    /* ========== НАВИГАЦИЯ ========== */
    .breadcrumb {
        background: linear-gradient(135deg, #0a1628 0%, #1a2942 100%);
        border: 1px solid #00f5d4;
        border-radius: 8px;
        padding: 12px 20px;
        margin: 10px 0;
        font-size: 1.1rem;
        color: #00f5d4;
    }
    
    /* ========== СЕКЦИИ ФИЛЬТРОВ ========== */
    .filter-section {
        background: linear-gradient(135deg, #0a0f1a 0%, #111827 100%);
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
    }
    
    /* ========== КАРТОЧКИ ПЛАНОВИКОВ ========== */
    .planner-card {
        background: linear-gradient(135deg, #0a1628 0%, #1a2942 100%);
        border: 1px solid #00f5d4;
        border-radius: 8px;
        padding: 15px;
        margin: 8px 0;
    }
    
    .rm-card {
        background: linear-gradient(135deg, #1a1628 0%, #2a1942 100%);
        border: 1px solid #ff0055;
        border-radius: 8px;
        padding: 15px;
        margin: 8px 0;
    }
    
    /* ========== БЕЙДЖИ ========== */
    .no-data-badge {
        background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
        border: 1px dashed #666;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #888;
        text-align: center;
    }
    
    /* ========== КЛИКАБЕЛЬНЫЕ ЭЛЕМЕНТЫ ========== */
    .clickable-card {
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .clickable-card:hover {
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(0,245,212,0.3);
    }
</style>
"""
