# -*- coding: utf-8 -*-
"""
config/font_config.py — Размеры шрифтов S/M/L

Все вкладки импортируют get_font_sizes() и подставляют жёстко в:
- st.html() heatmap таблицы
- Plotly графики (textfont, tickfont)
- BIG_FONT, HOVER_STYLE
"""

import streamlit as st


FONT_PRESETS = {
    'S': {
        'table_name': 13,      # Название в heatmap таблице
        'table_value': 12,     # Числа в heatmap
        'table_header': 11,    # Заголовки таблицы
        'table_deviation': 14, # Отклонение (жирный)
        'plotly_text': 13,     # Подписи на графиках Plotly
        'plotly_tick': 12,     # Оси Plotly
        'plotly_title': 16,    # Заголовок графика
        'donut_pct': 14,       # % на бублике
        'donut_center': 22,    # Центр бублика
        'donut_legend': 11,    # Легенда бублика
        'bar_label': 11,       # Подпись столбца
        'big_font': 14,        # BIG_FONT base
        'kpi_value': 24,       # Числа KPI
        'kpi_label': 12,       # Подписи KPI
        'kpi_title': 22,       # Заголовок "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ"
    },
    'M': {
        'table_name': 16,
        'table_value': 15,
        'table_header': 14,
        'table_deviation': 17,
        'plotly_text': 18,
        'plotly_tick': 16,
        'plotly_title': 20,
        'donut_pct': 22,
        'donut_center': 32,
        'donut_legend': 16,
        'bar_label': 16,
        'big_font': 18,
        'kpi_value': 36,
        'kpi_label': 16,
        'kpi_title': 30,
    },
    'L': {
        'table_name': 18,
        'table_value': 16,
        'table_header': 15,
        'table_deviation': 19,
        'plotly_text': 22,
        'plotly_tick': 20,
        'plotly_title': 28,
        'donut_pct': 36,
        'donut_center': 52,
        'donut_legend': 22,
        'bar_label': 20,
        'big_font': 22,
        'kpi_value': 42,
        'kpi_label': 18,
        'kpi_title': 36,
    },
}


def get_font_sizes():
    """Возвращает dict с размерами для текущего выбора S/M/L."""
    key = st.session_state.get('font_size', 'M')
    return FONT_PRESETS.get(key, FONT_PRESETS['M'])


def get_big_font():
    """BIG_FONT для Plotly layouts."""
    fs = get_font_sizes()
    return dict(family="Arial, sans-serif", size=fs['big_font'], color="#FFFFFF")


def get_hover_style():
    """HOVER_STYLE для Plotly."""
    fs = get_font_sizes()
    return dict(bgcolor="#1a1a2e", bordercolor="#00f5d4",
                font=dict(size=fs['plotly_text'], color="#FFFFFF", family="Arial"))


def render_metric_row(metrics_list):
    """
    Рисует ряд метрик через st.html.
    metrics_list: list of (label, value) or (label, value, delta, delta_color)
    """
    import streamlit as _st
    fs = get_font_sizes()
    v_sz = fs.get('kpi_value', 32)
    l_sz = fs.get('kpi_label', 14)
    
    cells = ""
    for m in metrics_list:
        label, value = m[0], m[1]
        delta = m[2] if len(m) > 2 else None
        dc = m[3] if len(m) > 3 else "#888"
        delta_html = f'<div style="font-size:{l_sz}px; color:{dc}; margin-top:2px;">{delta}</div>' if delta else ""
        cells += (
            f'<div style="flex:1; min-width:0;">'
            f'<div style="font-size:{l_sz}px; color:#00f5d4; font-weight:700;">{label}</div>'
            f'<div style="font-size:{v_sz}px; color:#fff; font-weight:700; line-height:1.3;">{value}</div>'
            f'{delta_html}</div>'
        )
    _st.html(f'<div style="display:flex; gap:8px; font-family:Arial,sans-serif; padding:8px 0;">{cells}</div>')


def render_unified_heatmap(df_data, name_col, key_prefix, extra_cols=None):
    """
    Единая heatmap-таблица: красный (перерасход) → зелёный (экономия).
    extra_cols: list of (col_name, header, align) для доп. колонок (ЕО и т.д.)
    """
    import streamlit as _st
    
    if len(df_data) == 0:
        return
    fs = get_font_sizes()
    abs_max = df_data['Отклонение'].abs().max()
    if abs_max == 0:
        abs_max = 1

    rows = []
    for i, (_, row) in enumerate(df_data.iterrows()):
        val = row['Отклонение']
        intensity = min(abs(val) / abs_max, 1.0)
        if val >= 0:
            r = int(40 + intensity * 180)
            g, b = 10, int(20 + intensity * 30)
            tc = '#ff6b6b' if intensity > 0.2 else '#ff9999'
            sign = "+"
        else:
            r = 10
            g = int(40 + intensity * 140)
            b = int(30 + intensity * 80)
            tc = '#6bffb8' if intensity > 0.2 else '#99ffcc'
            sign = ""
        bg = f"rgb({r},{g},{b})"
        name = str(row[name_col])
        
        extra_tds = ''
        if extra_cols:
            for col_name, _, align in extra_cols:
                if col_name in row.index:
                    extra_tds += (f'<td style="padding:10px 12px; font-size:{fs["table_value"]}px; '
                                  f'color:#ccc; text-align:{align};">{int(row[col_name])}</td>')

        rows.append(
            f'<tr style="background:{bg}; border-bottom:1px solid #333;">'
            f'<td style="padding:10px 14px; font-size:{fs["table_name"]}px; color:#fff; max-width:350px; '
            f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{name}">'
            f'{i+1}. {name}</td>'
            f'<td style="padding:10px 12px; font-size:{fs["table_value"]}px; color:#ccc; text-align:center;">{int(row["Заказов"])}</td>'
            f'{extra_tds}'
            f'<td style="padding:10px 12px; font-size:{fs["table_value"]}px; color:#e0e0e0; text-align:right;">'
            f'{_fmt_short_val(row["План"])} ₽</td>'
            f'<td style="padding:10px 12px; font-size:{fs["table_value"]}px; color:#e0e0e0; text-align:right;">'
            f'{_fmt_short_val(row["Факт"])} ₽</td>'
            f'<td style="padding:10px 12px; font-size:{fs["table_deviation"]}px; font-weight:bold; color:{tc}; text-align:right;">'
            f'{sign}{_fmt_short_val(val)} ₽</td>'
            f'</tr>'
        )

    extra_ths = ''
    if extra_cols:
        for _, header, align in extra_cols:
            extra_ths += f'<th style="padding:10px 12px; color:#aaa; text-align:{align}; font-size:{fs["table_header"]}px;">{header}</th>'

    html = (
        '<div style="overflow-x:auto; border-radius:8px; border:1px solid #333; margin:8px 0;">'
        '<table style="width:100%; border-collapse:collapse; font-family:Arial,sans-serif;">'
        f'<thead><tr style="background:#0a0a1a; border-bottom:2px solid #444;">'
        f'<th style="padding:10px 14px; color:#aaa; text-align:left; font-size:{fs["table_header"]}px;">Наименование</th>'
        f'<th style="padding:10px 12px; color:#aaa; text-align:center; font-size:{fs["table_header"]}px;">Заказов</th>'
        f'{extra_ths}'
        f'<th style="padding:10px 12px; color:#aaa; text-align:right; font-size:{fs["table_header"]}px;">План</th>'
        f'<th style="padding:10px 12px; color:#aaa; text-align:right; font-size:{fs["table_header"]}px;">Факт</th>'
        f'<th style="padding:10px 12px; color:#aaa; text-align:right; font-size:{fs["table_header"]}px;">Отклонение</th>'
        '</tr></thead><tbody>'
        + ''.join(rows)
        + '</tbody></table></div>'
    )
    _st.html(html)


def _fmt_short_val(val):
    """Форматирование для heatmap."""
    import pandas as _pd
    if _pd.isna(val) or val == 0:
        return "0"
    abs_val = abs(val)
    sign = "" if val >= 0 else "-"
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}Млрд"
    elif abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}М"
    elif abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}К"
    else:
        return f"{sign}{abs_val:.1f}"
