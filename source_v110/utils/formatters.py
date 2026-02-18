# -*- coding: utf-8 -*-
"""
utils/formatters.py — Форматирование чисел

Функции для красивого отображения чисел в интерфейсе.
"""

import pandas as pd


def fmt(n):
    """
    Форматирование числа с пробелами разрядов.
    
    Примеры:
        fmt(1234567) → "1 234 567"
        fmt(None) → "0"
        fmt("abc") → "abc"
    """
    try:
        if pd.isna(n):
            return "0"
        return "{:,.0f}".format(float(n)).replace(",", " ")
    except:
        return str(n)


def fmt_sign(n):
    """
    Форматирование числа со знаком (+/−).
    
    Примеры:
        fmt_sign(1000) → "+1 000"
        fmt_sign(-500) → "−500"
        fmt_sign(0) → "0"
    """
    try:
        if pd.isna(n):
            return "0"
        val = float(n)
        formatted = "{:,.0f}".format(abs(val)).replace(",", " ")
        if val > 0:
            return f"+{formatted}"
        elif val < 0:
            return f"−{formatted}"
        else:
            return "0"
    except:
        return str(n)


def fmt_pct(n, decimals=1):
    """
    Форматирование процентов.
    
    Примеры:
        fmt_pct(0.156) → "15.6%"
        fmt_pct(1.5) → "150.0%"
        fmt_pct(0.156, 0) → "16%"
    """
    try:
        if pd.isna(n):
            return "0%"
        val = float(n) * 100 if abs(float(n)) <= 1 else float(n)
        return f"{val:.{decimals}f}%"
    except:
        return "0%"
