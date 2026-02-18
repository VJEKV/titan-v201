# -*- coding: utf-8 -*-
"""
config/settings.py — Настройки по умолчанию

Инициализация session_state, пороги методов.
"""

import streamlit as st
from .constants import HIERARCHY_LEVELS, METHODS_RISK


# ============================================
# ПОРОГИ ПО УМОЛЧАНИЮ
# ============================================
DEFAULT_THRESHOLDS = {
    "C1-M1: Перерасход бюджета": 20,              # % превышения
    "C1-M6: Аномалия по истории ТМ": 140,         # % от медианы (140 = 1.4x)
    "C1-M9: Незавершённые работы": 0,             # нет порога
    "C2-M2: Проблемное оборудование": 5,          # кол-во заказов на ЕО
    "NEW-9: Формальное закрытие в декабре": 50,   # коэфф. быстроты (50 = в 2 раза быстрее)
    "NEW-10: Возвраты статусов": 3                # кол-во возвратов
}


def init_session_state():
    """
    Инициализация session_state при первом запуске.
    """
    
    # Фильтры иерархии
    if 'hierarchy_filters' not in st.session_state:
        st.session_state.hierarchy_filters = {
            level['key']: [] for level in HIERARCHY_LEVELS
        }
    
    # Дополнительные фильтры
    if 'extra_filters' not in st.session_state:
        st.session_state.extra_filters = {
            'search': '',
            'vid': [],
            'vid_kod': [],      # <-- НОВЫЙ: фильтр по коду вида заказа
            'abc': [],
            'stat': [],
            'rm': [],
            'ingrp': [],
            'mestopol': [],
            'vid_rabot': [],
            'maufnr': [],
            'dogovor': [],
            'klass': [],
            'date_from': None,
            'date_to': None
        }
    
    # Пороги методов риска
    if 'method_thresholds' not in st.session_state:
        st.session_state.method_thresholds = DEFAULT_THRESHOLDS.copy()
    
    # Порог превышения сроков (для TAB СРОКИ)
    if 'delay_threshold' not in st.session_state:
        st.session_state.delay_threshold = 30


def reset_all_filters():
    """
    Сброс всех фильтров к значениям по умолчанию.
    """
    for key in st.session_state.hierarchy_filters:
        st.session_state.hierarchy_filters[key] = []
    
    st.session_state.extra_filters = {
        'search': '', 
        'vid': [], 
        'vid_kod': [],      # <-- НОВЫЙ
        'abc': [], 
        'stat': [],
        'rm': [], 
        'ingrp': [], 
        'mestopol': [], 
        'vid_rabot': [],
        'maufnr': [], 
        'dogovor': [], 
        'klass': [],
        'date_from': None, 
        'date_to': None
    }


def reset_method_thresholds():
    """
    Сброс порогов методов к значениям по умолчанию.
    """
    st.session_state.method_thresholds = DEFAULT_THRESHOLDS.copy()
