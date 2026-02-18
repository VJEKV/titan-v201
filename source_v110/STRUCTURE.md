# ТИТАН Аудит ТОРО v.110 — Карта модулей

## 📁 Структура проекта

```
toro_modules/
│
├── STRUCTURE.md              # ← ВЫ ЗДЕСЬ (карта проекта)
├── BUILD.py                  # Сборщик в один файл (опционально)
├── app.py                    # Точка входа: streamlit run app.py
│
├── config/                   # ⚙️ КОНФИГУРАЦИЯ
│   ├── __init__.py           # Экспорт модулей конфига
│   ├── styles.py             # CSS стили INDUSTRIAL SUPREME
│   ├── constants.py          # METHODS_RISK, HIERARCHY_LEVELS, справочники
│   └── settings.py           # Пороги по умолчанию, session_state
│
├── core/                     # 🔧 ЯДРО ОБРАБОТКИ ДАННЫХ
│   ├── __init__.py           # Экспорт ядра
│   ├── data_loader.py        # load_file(), detect_export_format()
│   ├── data_processor.py     # process_data(), aggregate_status_history()
│   ├── aggregates.py         # compute_aggregates()
│   └── risk_scoring.py       # METHODS_RISK логика, get_logic()
│
├── components/               # 🧩 UI КОМПОНЕНТЫ
│   ├── __init__.py           # Экспорт компонентов
│   ├── sidebar.py            # render_sidebar() — 5 секций фильтров
│   ├── kpi_block.py          # render_kpi() — 3 строки показателей
│   └── charts.py             # create_method_donut(), общие графики
│
├── tabs/                     # 📊 ВКЛАДКИ ДАШБОРДА
│   ├── __init__.py           # Экспорт вкладок
│   ├── tab_finance.py        # TAB 1: ФИНАНСЫ
│   ├── tab_timeline.py       # TAB 2: СРОКИ
│   ├── tab_work_types.py     # TAB 3: ВИДЫ РАБОТ
│   ├── tab_planners.py       # TAB 4: ПЛАНОВИКИ
│   ├── tab_workplaces.py     # TAB 5: РАБ.МЕСТА
│   ├── tab_risks.py          # TAB 6: РИСКИ
│   └── tab_quality.py        # TAB 7: C4 КАЧЕСТВО
│
└── utils/                    # 🛠️ УТИЛИТЫ
    ├── __init__.py           # Экспорт утилит
    ├── formatters.py         # fmt(), fmt_sign(), fmt_pct()
    ├── parsers.py            # fast_parse_series(), safe_parse_datetime()
    ├── filters.py            # apply_hierarchy_filters(), build_breadcrumb()
    └── export.py             # create_excel_download()
```

---

## 📋 Содержание модулей

### config/styles.py
- **Что:** CSS стили INDUSTRIAL SUPREME
- **Экспорт:** `STYLES`
- **Менять когда:** изменение цветов, шрифтов, отступов

### config/constants.py
- **Что:** `METHODS_RISK`, `HIERARCHY_LEVELS`, `ВНЕПЛАНОВЫЕ_ВИДЫ`
- **Экспорт:** все константы
- **Менять когда:** добавление метода риска, изменение справочников

### config/settings.py
- **Что:** `init_session_state()`, `DEFAULT_THRESHOLDS`
- **Экспорт:** функции инициализации
- **Менять когда:** изменение порогов по умолчанию

---

### core/data_loader.py
- **Что:** `load_file()`, `detect_export_format()`
- **Менять когда:** поддержка новых форматов

### core/data_processor.py
- **Что:** `process_data()`, `aggregate_status_history()`
- **Менять когда:** новые поля в выгрузке SAP

### core/aggregates.py
- **Что:** `compute_aggregates()`
- **Менять когда:** новые агрегаты для методов

### core/risk_scoring.py
- **Что:** `get_logic()`, `apply_risk_scoring()`
- **Менять когда:** добавление/изменение методов риска

---

### components/sidebar.py
- **Что:** 5 секций фильтров
- **Менять когда:** добавление фильтров

### components/kpi_block.py
- **Что:** 3 строки KPI + карточки максимумов
- **Менять когда:** добавление метрик

### components/charts.py
- **Что:** `create_method_donut()`, `CHART_FONT`
- **Менять когда:** новые типы графиков

---

### tabs/tab_*.py
| Файл | Вкладка | Содержание |
|------|---------|------------|
| tab_finance.py | ФИНАНСЫ | TOP-20 ТМ, ABC с ЕО |
| tab_timeline.py | СРОКИ | Превышения, слайдер порога |
| tab_work_types.py | ВИДЫ РАБОТ | Плановые/внеплановые |
| tab_planners.py | ПЛАНОВИКИ | INGRP, USER, HEATMAP |
| tab_workplaces.py | РАБ.МЕСТА | Анализ по РМ |
| tab_risks.py | РИСКИ | 6 методов с бубликами |
| tab_quality.py | C4 КАЧЕСТВО | Полнота данных |

---

## 🚀 Быстрый старт

```bash
# Запуск
cd toro_modules
streamlit run app.py

# Сборка в один файл
python BUILD.py
```

## 🔧 Типичные задачи

| Задача | Файл |
|--------|------|
| Добавить метод NEW-15 | `config/constants.py` + `core/risk_scoring.py` |
| Изменить вкладку СРОКИ | `tabs/tab_timeline.py` |
| Новый фильтр | `components/sidebar.py` |
| Изменить цвета | `config/styles.py` |
| Новая метрика KPI | `components/kpi_block.py` |
