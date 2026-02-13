import { useState, useEffect } from 'react';
import { C } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet } from '../api/client';
import TagSelect from './TagSelect';

/**
 * Боковая панель фильтров с тегами и datepicker
 */
export default function Sidebar() {
  const { sessionId, filters, updateFilter, updateHierarchy, resetFilters, thresholds, updateThreshold } = useFilters();
  const [options, setOptions] = useState(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    apiGet('/api/filters/options', { session_id: sessionId })
      .then(data => setOptions(data))
      .catch(() => {});
  }, [sessionId]);

  if (!sessionId) return null;

  const hierarchyLevels = [
    { key: 'БЕ', label: 'Балансовая единица' },
    { key: 'ЗАВОД', label: 'Завод' },
    { key: 'ПРОИЗВОДСТВО', label: 'Производство' },
    { key: 'ЦЕХ', label: 'Цех' },
    { key: 'УСТАНОВКА', label: 'Установка' },
    { key: 'ЕО', label: 'Ед. оборудования' },
  ];

  const inputStyle = {
    width: '100%', marginTop: 2, padding: '6px 8px',
    background: C.bg, border: `1px solid ${C.border}`,
    borderRadius: 6, color: C.text, fontSize: 12, outline: 'none',
  };

  return (
    <aside style={{
      width: collapsed ? 48 : 300,
      minHeight: '100vh',
      background: C.surface,
      borderRight: `1px solid ${C.border}`,
      padding: collapsed ? '12px 8px' : '16px',
      transition: 'width 0.2s',
      overflowY: 'auto',
      overflowX: 'hidden',
      flexShrink: 0,
    }}>
      <button onClick={() => setCollapsed(!collapsed)} style={{
        background: 'none', border: 'none', color: C.muted, cursor: 'pointer',
        fontSize: 18, marginBottom: 12, width: '100%', textAlign: collapsed ? 'center' : 'right',
      }}>
        {collapsed ? '▶' : '◀'}
      </button>

      {!collapsed && (
        <>
          {/* Поиск */}
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: C.muted, textTransform: 'uppercase' }}>Поиск</label>
            <input
              type="text"
              value={filters.search}
              onChange={e => updateFilter('search', e.target.value)}
              placeholder="ID, текст, ТМ..."
              style={{ ...inputStyle, padding: '8px 10px', fontSize: 13 }}
            />
          </div>

          {/* Даты */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>
              Период (план. начало)
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 10, color: C.dim }}>Дата с</label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={e => updateFilter('date_from', e.target.value)}
                  style={inputStyle}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 10, color: C.dim }}>Дата по</label>
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={e => updateFilter('date_to', e.target.value)}
                  style={inputStyle}
                />
              </div>
            </div>
          </div>

          {/* Иерархия — теги */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>
              Иерархия
            </div>
            {hierarchyLevels.map(level => {
              const opts = options?.hierarchy?.[level.key] || [];
              if (opts.length === 0) return null;
              return (
                <TagSelect
                  key={level.key}
                  label={level.label}
                  options={opts}
                  value={filters.hierarchy[level.key] || []}
                  onChange={vals => updateHierarchy(level.key, vals)}
                  placeholder={`Выбрать ${level.label.toLowerCase()}...`}
                />
              );
            })}
          </div>

          {/* Фильтры — теги */}
          {[
            { key: 'vid', label: 'Вид работ' },
            { key: 'abc', label: 'ABC' },
            { key: 'stat', label: 'Статус' },
          ].map(({ key, label }) => {
            const opts = options?.[key] || [];
            if (opts.length === 0) return null;
            return (
              <TagSelect
                key={key}
                label={label}
                options={opts}
                value={filters[key] || []}
                onChange={vals => updateFilter(key, vals)}
                placeholder={`Выбрать...`}
              />
            );
          })}

          {/* Пороги методов */}
          <div style={{ marginBottom: 12, marginTop: 12 }}>
            <div style={{ fontSize: 11, color: C.muted, textTransform: 'uppercase', marginBottom: 8 }}>
              Пороги методов
            </div>
            {[
              { key: 'C1-M1: Перерасход бюджета', label: 'C1-M1: Перерасход бюджета', unit: '%', min: 0, max: 100, color: '#f43f5e' },
              { key: 'C1-M6: Аномалия по истории ТМ', label: 'C1-M6: Аномалия по истории ТМ', unit: '%', min: 100, max: 300, color: '#fbbf24' },
              { key: 'C2-M2: Проблемное оборудование', label: 'C2-M2: Проблемное оборудование', unit: 'шт', min: 2, max: 20, color: '#fb923c' },
              { key: 'NEW-9: Формальное закрытие в декабре', label: 'NEW-9: Формальное закрытие', unit: '%', min: 30, max: 70, color: '#22d3ee' },
              { key: 'NEW-10: Возвраты статусов', label: 'NEW-10: Возвраты статусов', unit: 'шт', min: 1, max: 10, color: '#34d399' },
            ].map(t => (
              <div key={t.key} style={{ marginBottom: 10, padding: '6px 8px', borderRadius: 6, background: `${t.color}08`, borderLeft: `3px solid ${t.color}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                  <label style={{ fontSize: 10, color: C.muted }}>{t.label}</label>
                  <span style={{ fontSize: 11, color: t.color, fontWeight: 600 }}>
                    {thresholds[t.key] || 0} {t.unit}
                  </span>
                </div>
                <input
                  type="range"
                  min={t.min}
                  max={t.max}
                  value={thresholds[t.key] || 0}
                  onChange={e => updateThreshold(t.key, Number(e.target.value))}
                  style={{ width: '100%', accentColor: t.color, marginTop: 2 }}
                />
              </div>
            ))}
          </div>

          <button onClick={resetFilters} style={{
            width: '100%', padding: '8px', marginTop: 8,
            background: C.bg, border: `1px solid ${C.border}`,
            borderRadius: 6, color: C.muted, cursor: 'pointer', fontSize: 12,
          }}>
            Сбросить фильтры
          </button>
        </>
      )}
    </aside>
  );
}
