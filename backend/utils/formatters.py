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


def fmt_downtime(seconds):
    """Форматирование простоя: секунды → 'X дн. Y час.' """
    try:
        if pd.isna(seconds) or seconds is None:
            return "0"
        val = float(seconds)
        if val <= 0:
            return "0"
        total_hours = val / 3600
        days = int(total_hours // 24)
        hours = int(total_hours % 24)
        if days > 0:
            return f"{days} дн. {hours} час."
        return f"{hours} час."
    except Exception:
        return "0"


def fmt_date_styled(date_val, source):
    """Возвращает dict {text, color} для даты с меткой источника."""
    if pd.isna(date_val):
        return {"text": "— нет даты —", "color": "#f43f5e"}
    text = date_val.strftime('%d.%m.%Y')
    if source == 'FACT':
        return {"text": text, "color": "#34d399"}
    elif source == 'NOTIFY':
        return {"text": text + " \u25cb", "color": "#38bdf8"}
    elif source == 'PLAN':
        return {"text": text + " \u2022", "color": "#fbbf24"}
    return {"text": "— нет даты —", "color": "#f43f5e"}
