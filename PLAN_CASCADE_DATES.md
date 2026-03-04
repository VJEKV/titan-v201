# План: Стратегия каскадных дат для ТИТАН v200

## Контекст

Фактические даты (ZZFACTBEG/ZZFACTEND) заполнены только у ~50% заказов. Плановые даты (GSTRP/GLTRP) содержат мусор 1970/1980 годов (Unix epoch, SAP defaults). Это искажает аналитику: бар-чарт по месяцам, риск-скоринг, фильтрацию по периоду.

Решение: каскадные даты (факт → план, с отсечкой мусора < 2015), визуальная метка источника, сноска-легенда.

## Файлы для изменения

1. `backend/core/data_processor.py` — каскад дат, новые поля
2. `backend/core/risk_scoring.py` — DQ_Risk штраф за мусор, C1-M9 вес×0.7 для PLAN, NEW-9 строго FACT
3. `backend/api/routes_filters.py` — фильтр по периоду дат (date_from/date_to)
4. `backend/api/routes_kpi.py` — KPI по покрытию датами
5. `backend/utils/formatters.py` — функция форматирования дат с меткой источника
6. `frontend/src/components/DateFootnote.jsx` — **НОВЫЙ** — компонент сноски-легенды
7. `frontend/src/components/Sidebar.jsx` — DatePicker фильтр периода
8. `frontend/src/tabs/Finance.jsx` — Дата_Месяц вместо Начало, сноска над бар-чартом
9. `frontend/src/tabs/Timeline.jsx` — каскадные даты, сноска
10. `frontend/src/tabs/Risks.jsx` — сноска над TOP-50
11. `frontend/src/tabs/Quality.jsx` — KPI по покрытию датами
12. `frontend/src/tabs/Orders.jsx` — цветовое форматирование дат, сноска
13. `frontend/src/tabs/Workplaces.jsx` — сноска если есть даты

---

## Шаг 1: `core/data_processor.py`

В `process_data()` после парсинга дат (строка ~229) добавить:

```python
DATE_CUTOFF = pd.Timestamp('2015-01-01')

# Валидация: всё < 2015 → NaT
for col in ['Начало', 'Конец', 'Факт_Начало', 'Факт_Конец']:
    if col in df.columns:
        df.loc[df[col] < DATE_CUTOFF, col] = pd.NaT

# Каскадные даты
df['Дата_Начало'] = df['Факт_Начало'].where(df['Факт_Начало'].notna(), df['Начало'])
df['Дата_Конец'] = df['Факт_Конец'].where(df['Факт_Конец'].notna(), df['Конец'])
df['Дата_Месяц'] = df['Дата_Начало']  # для группировки по месяцам

# Источник дат
df['Источник_Дат'] = 'NONE'
mask_fact = df['Факт_Начало'].notna()
mask_plan = (~mask_fact) & df['Начало'].notna()
df.loc[mask_fact, 'Источник_Дат'] = 'FACT'
df.loc[mask_plan, 'Источник_Дат'] = 'PLAN'
```

Обновить расчёт длительности: использовать Дата_Начало/Дата_Конец, убрать старую проверку `dt.year > 1971`.

Добавить `Дата_Начало`, `Дата_Конец`, `Дата_Месяц`, `Источник_Дат` в сериализацию/десериализацию.

## Шаг 2: `frontend/src/components/Sidebar.jsx` — фильтр дат

В Sidebar между секцией ПОИСК и ИЕРАРХИЯ добавить:

```jsx
{/* Секция ПЕРИОД */}
<div className="sidebar-section">
  <div className="sidebar-section-title">ПЕРИОД</div>
  <div style={{ display: "flex", gap: "8px" }}>
    <div style={{ flex: 1 }}>
      <label style={{ fontSize: "11px", color: C.muted }}>Дата с</label>
      <input type="date" value={filters.dateFrom || ""}
        onChange={e => setFilter("dateFrom", e.target.value)}
        style={{ backgroundColor: C.bg, color: C.text, border: `1px solid ${C.border}` }} />
    </div>
    <div style={{ flex: 1 }}>
      <label style={{ fontSize: "11px", color: C.muted }}>Дата по</label>
      <input type="date" value={filters.dateTo || ""}
        onChange={e => setFilter("dateTo", e.target.value)}
        style={{ backgroundColor: C.bg, color: C.text, border: `1px solid ${C.border}` }} />
    </div>
  </div>
</div>
```

### `backend/api/` — фильтрация по периоду

Во все роуты вкладок добавить query-параметры `date_from`/`date_to`. В `backend/utils/filters.py`:

```python
# Логика пересечения: заказ жил в выбранном периоде
# Заказы с NONE (обе даты NaT) — всегда проходят
if date_from:
    mask_has_dates = df_f['Дата_Конец'].notna()
    mask_pass = ~mask_has_dates | (df_f['Дата_Конец'] >= pd.Timestamp(date_from))
    df_f = df_f[mask_pass]
if date_to:
    mask_has_dates = df_f['Дата_Начало'].notna()
    mask_pass = ~mask_has_dates | (df_f['Дата_Начало'] <= pd.Timestamp(date_to))
    df_f = df_f[mask_pass]
```

Добавить `dateFrom`/`dateTo` в `useFilters` контекст и передавать в API-запросы.

## Шаг 3: KPI по датам

В `backend/api/routes_kpi.py` добавить в ответ поля покрытия датами:

```python
date_stats = {
    "no_dates": int((df['Источник_Дат'] == 'NONE').sum()),
    "fact_dates": int((df['Источник_Дат'] == 'FACT').sum()),
    "plan_dates": int((df['Источник_Дат'] == 'PLAN').sum()),
}
```

Во фронтенде (`App.jsx` или отдельный `KpiRow`) отрисовать три доп. карточки:
- БЕЗ ДАТ — бордер `C.danger`
- ФАКТ — бордер `C.cyan`
- ПЛАН — бордер `C.cyan`

## Шаг 4: `frontend/src/components/DateFootnote.jsx` — НОВЫЙ файл

```jsx
import { C } from '../theme/arctic';

export default function DateFootnote() {
  return (
    <div style={{ fontSize: "11px", marginBottom: 8, color: C.muted }}>
      <span style={{ color: C.cyan }}>Даты: </span>
      <span style={{ color: "#fff" }}>белый</span> — фактическая,{" "}
      <span style={{ color: C.warning }}>жёлтый</span> — плановая,{" "}
      <span style={{ color: C.danger }}>нет данных</span> — отсутствует
    </div>
  );
}
```

Размещается **НАД** (не под) каждым компонентом с датами.

## Шаг 5: `utils/formatters.py` — форматирование дат

Добавить функцию:

```python
def fmt_date_styled(date_val, source):
    """Возвращает dict {text, color} для отображения даты с меткой источника."""
    if pd.isna(date_val):
        return {"text": "— нет даты —", "color": "#ff0055"}
    text = date_val.strftime('%d.%m.%Y')
    if source == 'FACT':
        return {"text": text, "color": "#ffffff"}
    elif source == 'PLAN':
        return {"text": text + " •", "color": "#ffd700"}
    return {"text": "— нет даты —", "color": "#ff0055"}
```

## Шаг 6: `core/risk_scoring.py`

1. **DQ_Risk**: расширить — мусорные даты < 2015 уже будут NaT после шага 1, поэтому isna() автоматически их поймает. Ничего менять не нужно — работает из коробки.

2. **C1-M9**: добавить пониженный вес для PLAN дат:
```python
# Если источник дат = PLAN, снижаем score × 0.7
if 'Источник_Дат' in df.columns:
    is_plan = df['Источник_Дат'] == 'PLAN'
    score = score.where(~is_plan, score * 0.7)
```

3. **NEW-9**: использовать только оригинальные `Факт_Конец` (не каскадную Дата_Конец). Уже так реализовано — не меняем.

## Шаг 7: Вкладки — подключение каскадных дат и сносок

### Finance.jsx
- Backend: `routes_finance.py` — группировка по `Дата_Месяц` вместо `Начало`
- Frontend: `<DateFootnote />` **НАД** бар-чартом

### Timeline.jsx
- Backend: `routes_timeline.py` — группировка по `Дата_Месяц`, KPI по `Дата_Начало`
- Frontend: `<DateFootnote />` над графиками

### Risks.jsx
- Frontend: `<DateFootnote />` над TOP-50 таблицей

### Quality.jsx
- Backend: `routes_quality.py` — добавить секцию "Покрытие датами": % FACT / PLAN / NONE
- Frontend: отобразить покрытие датами

### Orders.jsx
- Backend: `routes_orders.py` — отдавать `Дата_Начало`, `Дата_Конец`, `Источник_Дат`
- Frontend: cellStyle — белый для FACT, жёлтый для PLAN, красный для NONE
- Frontend: `<DateFootnote />` над таблицей

### Workplaces.jsx
- Frontend: `<DateFootnote />` если есть даты в таблице

---

## Порядок реализации

1. `backend/core/data_processor.py` — каскад дат (фундамент)
2. `backend/utils/formatters.py` — fmt_date_styled
3. `backend/utils/filters.py` — фильтрация по date_from/date_to
4. `backend/api/routes_kpi.py` — KPI покрытия датами
5. `backend/core/risk_scoring.py` — C1-M9 вес×0.7
6. `backend/api/routes_finance.py` — Дата_Месяц
7. `backend/api/routes_timeline.py` — Дата_Месяц
8. `backend/api/routes_orders.py` — Источник_Дат в ответе
9. `backend/api/routes_quality.py` — покрытие датами
10. `frontend/src/components/DateFootnote.jsx` — новый компонент
11. `frontend/src/components/Sidebar.jsx` — DatePicker фильтр периода
12. `frontend/src/tabs/Finance.jsx` — сноска
13. `frontend/src/tabs/Timeline.jsx` — сноска
14. `frontend/src/tabs/Orders.jsx` — цветные даты + сноска
15. `frontend/src/tabs/Risks.jsx` — сноска
16. `frontend/src/tabs/Quality.jsx` — покрытие датами
17. `frontend/src/tabs/Workplaces.jsx` — сноска

## Проверка

```bash
cd /root/titan-v200

# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# → http://localhost:8000/docs (Swagger UI)

# Frontend
cd ../frontend && npm install && npm run dev
# → http://localhost:5173

# Загрузить test_data.csv
# Проверить: KPI с датами, фильтр периода, сноски над таблицами
# Проверить: таблица заказов — цвета дат (белый/жёлтый/красный)
# Проверить: бар-чарт финансов группируется по Дата_Месяц
```
