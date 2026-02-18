# -*- coding: utf-8 -*-
"""
core/tm_loader.py — Загрузка справочника структуры ТМ

Загружает tm_structure.json и предоставляет функции для:
- Получения иерархии по коду ТМ
- Получения ТМ по коду ЕО
- Формирования отображаемых значений с наименованиями

ИСПОЛЬЗОВАНИЕ В data_processor.py:
    from core.tm_loader import get_hierarchy_by_eo, get_hierarchy_by_tm
    
    # По коду ЕО получаем всю иерархию
    hier = get_hierarchy_by_eo('101000005640')
    # {'tm_code': 'ST01.0101.CD01', 'производство': 'ST01', 'цех': 'ST01.01', ...}
"""

import json
import os
import streamlit as st

# Глобальный кэш справочников
_TM_HIERARCHY = None
_EO_TO_TM = None
_LOADED = False


def _get_json_path():
    """Ищет tm_structure.json в разных местах."""
    possible_paths = [
        'tm_structure.json',
        os.path.join(os.path.dirname(__file__), 'tm_structure.json'),
        os.path.join(os.path.dirname(__file__), '..', 'tm_structure.json'),
        '/mnt/user-data/uploads/tm_structure.json',
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def _load_structure():
    """Загружает справочники из JSON (один раз)."""
    global _TM_HIERARCHY, _EO_TO_TM, _LOADED
    
    if _LOADED:
        return
    
    path = _get_json_path()
    if path:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _TM_HIERARCHY = data.get('tm_hierarchy', {})
            _EO_TO_TM = data.get('eo_to_tm', {})
        except Exception as e:
            print(f"Ошибка загрузки tm_structure.json: {e}")
            _TM_HIERARCHY = {}
            _EO_TO_TM = {}
    else:
        _TM_HIERARCHY = {}
        _EO_TO_TM = {}
    
    _LOADED = True


@st.cache_data(show_spinner=False)
def load_tm_structure():
    """
    Загрузка справочников с кэшированием Streamlit.
    
    Returns:
        tuple: (tm_hierarchy, eo_to_tm)
    """
    _load_structure()
    return _TM_HIERARCHY, _EO_TO_TM


def get_tm_by_eo(eo_code):
    """
    Получить код ТМ по коду ЕО.
    
    Args:
        eo_code: код ЕО (например '101000000064')
        
    Returns:
        str: код ТМ или None
    """
    _load_structure()
    return _EO_TO_TM.get(str(eo_code).strip())


def get_hierarchy_by_tm(tm_code):
    """
    Получить иерархию по коду ТМ.
    
    Args:
        tm_code: код ТМ (например 'ST01.0100.AT01')
        
    Returns:
        dict или None
    """
    _load_structure()
    return _TM_HIERARCHY.get(tm_code)


def get_hierarchy_by_eo(eo_code):
    """
    Получить полную иерархию по коду ЕО.
    
    Args:
        eo_code: код ЕО
        
    Returns:
        dict или None
    """
    tm_code = get_tm_by_eo(eo_code)
    if not tm_code:
        return None
    
    hierarchy = get_hierarchy_by_tm(tm_code)
    if not hierarchy:
        return None
    
    return {
        'tm_code': tm_code,
        'tm_name': hierarchy.get('название', ''),
        'производство_код': hierarchy.get('производство_код', ''),
        'производство_название': hierarchy.get('производство_название', ''),
        'цех_код': hierarchy.get('цех_код', ''),
        'цех_название': hierarchy.get('цех_название', ''),
        'установка_код': hierarchy.get('установка_код', ''),
        'установка_название': hierarchy.get('установка_название', '')
    }


def format_with_name(code, name):
    """Форматирует: 'КОД - Название' или 'Н/Д'."""
    if not code or code in ['', 'Н/Д', 'nan', 'None']:
        return 'Н/Д'
    if name:
        return f"{code} - {name}"
    return code


def get_production_display(code):
    """Получить отображаемое значение производства."""
    _load_structure()
    info = _TM_HIERARCHY.get(code, {})
    name = info.get('название', '') if info else ''
    return format_with_name(code, name)


def get_workshop_display(code):
    """Получить отображаемое значение цеха."""
    _load_structure()
    info = _TM_HIERARCHY.get(code, {})
    name = info.get('название', '') if info else ''
    return format_with_name(code, name)


def get_installation_display(code):
    """Получить отображаемое значение установки."""
    _load_structure()
    info = _TM_HIERARCHY.get(code, {})
    name = info.get('название', '') if info else ''
    return format_with_name(code, name)


def is_structure_loaded():
    """Проверяет, загружен ли справочник."""
    _load_structure()
    return len(_TM_HIERARCHY) > 0
