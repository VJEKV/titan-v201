# -*- coding: utf-8 -*-
"""
utils/formatters.py — Форматирование чисел
"""

import pandas as pd


def fmt(n):
    """Форматирование числа с пробелами разрядов."""
    try:
        if pd.isna(n):
            return "0"
        return "{:,.0f}".format(float(n)).replace(",", " ")
    except Exception:
        return str(n)


def fmt_sign(n):
    """Форматирование числа со знаком (+/−)."""
    try:
        if pd.isna(n):
            return "0"
        val = float(n)
        formatted = "{:,.0f}".format(abs(val)).replace(",", " ")
        if val > 0:
            return f"+{formatted}"
        elif val < 0:
            return f"\u2212{formatted}"
        else:
            return "0"
    except Exception:
        return str(n)


def fmt_pct(n, decimals=1):
    """Форматирование процентов."""
    try:
        if pd.isna(n):
            return "0%"
        val = float(n) * 100 if abs(float(n)) <= 1 else float(n)
        return f"{val:.{decimals}f}%"
    except Exception:
        return "0%"


def fmt_short(val):
    """Форматирование: 101.0М, 4.1М, 1.2Млрд, 371.0К."""
    if pd.isna(val) or val == 0:
        return "0"
    abs_val = abs(val)
    sign = "" if val >= 0 else "-"
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}\u041c\u043b\u0440\u0434"
    elif abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}\u041c"
    elif abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}\u041a"
    else:
        return f"{sign}{abs_val:.1f}"
