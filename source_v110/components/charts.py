# -*- coding: utf-8 -*-
"""
components/charts.py — Общие функции графиков

Стили и компоненты для Plotly визуализаций.
"""

import plotly.graph_objects as go


# Шрифт для всех графиков
CHART_FONT = dict(family="Arial, sans-serif", size=14, color="#FFFFFF")

# Цветовая палитра
COLORS = {
    'primary': '#00f5d4',      # Бирюзовый
    'danger': '#ff0055',       # Красный
    'warning': '#ffd700',      # Жёлтый
    'success': '#10b981',      # Зелёный
    'purple': '#8b5cf6',       # Фиолетовый
    'orange': '#ff6b35',       # Оранжевый
    'background': '#020408',   # Тёмный фон
    'card': '#1a1a2e',         # Фон карточки
}


def create_method_donut(triggered_count, total_count, method_name, color='#ff0055'):
    """
    Создать бублик (donut chart) для метода риска.
    
    Args:
        triggered_count: количество сработавших заказов
        total_count: общее количество заказов
        method_name: название метода (для отображения в центре)
        color: цвет заполненной части
        
    Returns:
        go.Figure: Plotly фигура
    """
    safe_count = max(total_count - triggered_count, 0)
    
    fig = go.Figure(go.Pie(
        values=[triggered_count, safe_count],
        labels=['Риск', 'Норма'],
        hole=0.7,
        marker=dict(colors=[color, '#00f5d4']),
        textinfo='none',
        hovertemplate="<b>%{label}</b><br>%{value} заказов<br>%{percent}<extra></extra>"
    ))
    
    # Текст в центре
    pct = (triggered_count / total_count * 100) if total_count > 0 else 0
    fig.add_annotation(
        text=f"<b>{triggered_count}</b><br><span style='font-size:32px'>{pct:.1f}%</span>",
        x=0.5, y=0.5,
        font=dict(size=32, color='#ff6b35'),
        showarrow=False
    )
    
    fig.update_layout(
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=360,
        width=360
    )
    
    return fig


def create_horizontal_bar(data, x_col, y_col, color='#00f5d4', title=None, height=400):
    """
    Создать горизонтальную столбчатую диаграмму.
    
    Args:
        data: DataFrame с данными
        x_col: колонка для значений (ось X)
        y_col: колонка для категорий (ось Y)
        color: цвет столбцов
        title: заголовок графика
        height: высота в пикселях
        
    Returns:
        go.Figure: Plotly фигура
    """
    fig = go.Figure(go.Bar(
        y=data[y_col].astype(str).str[:40],
        x=data[x_col],
        orientation='h',
        marker=dict(color=color, line=dict(color='#ffffff', width=1)),
        textposition='outside',
        textfont=dict(color='#ffffff', size=11)
    ))
    
    fig.update_layout(
        title=title,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=CHART_FONT,
        height=height,
        yaxis=dict(categoryorder='total ascending'),
        margin=dict(l=200, r=80)
    )
    
    return fig


def create_pie_chart(labels, values, colors=None, hole=0.45, height=400):
    """
    Создать круговую/кольцевую диаграмму.
    
    Args:
        labels: список меток
        values: список значений
        colors: список цветов (опционально)
        hole: размер отверстия (0 = круг, 0.5 = кольцо)
        height: высота в пикселях
        
    Returns:
        go.Figure: Plotly фигура
    """
    if colors is None:
        colors = [COLORS['danger'], COLORS['warning'], COLORS['primary'], 
                  COLORS['purple'], COLORS['success']]
    
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=hole,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textfont=dict(size=14, color='#ffffff')
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=CHART_FONT,
        height=height,
        legend=dict(font=dict(size=14, color='#ffffff'))
    )
    
    return fig
