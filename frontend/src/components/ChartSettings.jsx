import { useState, useEffect, useRef } from 'react';
import { C, CHART_PALETTES, FONT_SIZE_PRESETS, FONT_OPTIONS } from '../theme/arctic';

const LS_KEY = 'titan_chart_settings';

/** Получить глобальные настройки из localStorage (шрифт, размер) */
export function getChartSettings() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { font: 'Inter', fontSize: 'M', palette: 'ice' };
}

/** Сохранить глобальные настройки */
function saveSettings(s) {
  localStorage.setItem(LS_KEY, JSON.stringify(s));
}

/** Получить палитру для конкретного графика (по chartId) */
export function getChartPalette(chartId) {
  if (!chartId) return null;
  try {
    return localStorage.getItem(`titan_chart_palette_${chartId}`);
  } catch {}
  return null;
}

/** Сохранить палитру для конкретного графика */
function saveChartPalette(chartId, paletteKey) {
  if (chartId) {
    localStorage.setItem(`titan_chart_palette_${chartId}`, paletteKey);
  }
}

/** Хук для использования настроек с реактивным обновлением */
export function useChartSettings(chartId) {
  const [settings, setSettings] = useState(getChartSettings);
  const [localPalette, setLocalPalette] = useState(() => getChartPalette(chartId));

  useEffect(() => {
    const handler = (e) => {
      if (e.key === LS_KEY) setSettings(getChartSettings());
      if (chartId && e.key === `titan_chart_palette_${chartId}`) {
        setLocalPalette(getChartPalette(chartId));
      }
    };
    window.addEventListener('storage', handler);
    // Кастомное событие для обновления внутри одного окна
    const customHandler = () => {
      setSettings(getChartSettings());
      if (chartId) setLocalPalette(getChartPalette(chartId));
    };
    window.addEventListener('chart-settings-changed', customHandler);
    return () => {
      window.removeEventListener('storage', handler);
      window.removeEventListener('chart-settings-changed', customHandler);
    };
  }, [chartId]);

  // Палитра: сначала индивидуальная для графика, затем глобальная
  const activePalette = localPalette || settings.palette || 'ice';
  const paletteColors = CHART_PALETTES[activePalette]?.colors || CHART_PALETTES.ice.colors;
  const fontSizes = FONT_SIZE_PRESETS[settings.fontSize] || FONT_SIZE_PRESETS.M;

  return { ...settings, palette: activePalette, paletteColors, fontSizes };
}

/** Иконка шестерёнки SVG */
const GearIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M6.5 1L6.2 2.5C5.7 2.7 5.3 2.9 4.9 3.2L3.4 2.7L1.9 5.3L3.1 6.3C3.05 6.5 3 6.8 3 7C3 7.2 3.05 7.5 3.1 7.7L1.9 8.7L3.4 11.3L4.9 10.8C5.3 11.1 5.7 11.3 6.2 11.5L6.5 13H9.5L9.8 11.5C10.3 11.3 10.7 11.1 11.1 10.8L12.6 11.3L14.1 8.7L12.9 7.7C12.95 7.5 13 7.2 13 7C13 6.8 12.95 6.5 12.9 6.3L14.1 5.3L12.6 2.7L11.1 3.2C10.7 2.9 10.3 2.7 9.8 2.5L9.5 1H6.5Z"
      stroke={C.muted} strokeWidth="1.2" fill="none" />
    <circle cx="8" cy="7" r="2" stroke={C.muted} strokeWidth="1.2" fill="none" />
  </svg>
);

/**
 * Компонент настроек графика — шестерёнка с выпадающей панелью.
 * chartId — уникальный идентификатор графика для сохранения типа и палитры.
 * chartTypes — массив [{value, label}] доступных типов графика, null если переключение не нужно.
 * onChartTypeChange — callback при смене типа.
 * currentChartType — текущий тип.
 */
export default function ChartSettings({ chartId, chartTypes, currentChartType, onChartTypeChange }) {
  const [open, setOpen] = useState(false);
  const [settings, setLocal] = useState(getChartSettings);
  const [localPalette, setLocalPalette] = useState(() => getChartPalette(chartId));
  const panelRef = useRef(null);

  // Активная палитра для данного графика
  const activePalette = localPalette || settings.palette || 'ice';

  // Закрытие при клике вне панели
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Загрузка сохранённого типа графика
  useEffect(() => {
    if (chartId && onChartTypeChange) {
      try {
        const saved = localStorage.getItem(`titan_chart_type_${chartId}`);
        if (saved && chartTypes?.some(t => t.value === saved)) {
          onChartTypeChange(saved);
        }
      } catch {}
    }
  }, [chartId]);

  const update = (key, val) => {
    const next = { ...settings, [key]: val };
    setLocal(next);
    saveSettings(next);
    window.dispatchEvent(new Event('chart-settings-changed'));
  };

  const handlePaletteChange = (paletteKey) => {
    // Сохраняем палитру ТОЛЬКО для данного графика
    setLocalPalette(paletteKey);
    saveChartPalette(chartId, paletteKey);
    window.dispatchEvent(new Event('chart-settings-changed'));
  };

  const handleChartType = (val) => {
    if (chartId) localStorage.setItem(`titan_chart_type_${chartId}`, val);
    onChartTypeChange?.(val);
  };

  const btnStyle = (active) => ({
    padding: '4px 10px', borderRadius: 5, fontSize: 11, cursor: 'pointer', border: 'none',
    background: active ? `${C.accent}30` : C.bg, color: active ? C.accent : C.muted,
    fontWeight: active ? 600 : 400, transition: 'all 0.15s',
  });

  return (
    <div ref={panelRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button onClick={() => setOpen(!open)} title="Настройки графика"
        style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: 4,
          opacity: open ? 1 : 0.5, transition: 'opacity 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.opacity = 1}
        onMouseLeave={e => { if (!open) e.currentTarget.style.opacity = 0.5; }}>
        <GearIcon />
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 28, right: 0, zIndex: 50,
          background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10,
          padding: 14, minWidth: 240, boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}>
          {/* Шрифт */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: C.dim, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>Шрифт</div>
            <div style={{ display: 'flex', gap: 4 }}>
              {FONT_OPTIONS.map(f => (
                <button key={f} onClick={() => update('font', f)} style={{ ...btnStyle(settings.font === f), fontFamily: f }}>
                  {f.split(' ')[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Размер */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: C.dim, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>Размер шрифта</div>
            <div style={{ display: 'flex', gap: 4 }}>
              {['S', 'M', 'L'].map(s => (
                <button key={s} onClick={() => update('fontSize', s)} style={btnStyle(settings.fontSize === s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Палитра — ИНДИВИДУАЛЬНАЯ для данного графика */}
          <div style={{ marginBottom: chartTypes ? 10 : 0 }}>
            <div style={{ fontSize: 10, color: C.dim, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>Палитра (этот график)</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {Object.entries(CHART_PALETTES).map(([key, pal]) => (
                <button key={key} onClick={() => handlePaletteChange(key)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px',
                    borderRadius: 5, border: 'none', cursor: 'pointer',
                    background: activePalette === key ? `${C.accent}15` : 'transparent',
                  }}>
                  <div style={{ display: 'flex', gap: 2 }}>
                    {pal.colors.slice(0, 5).map((c, i) => (
                      <div key={i} style={{ width: 14, height: 14, borderRadius: 3, background: c }} />
                    ))}
                  </div>
                  <span style={{ fontSize: 11, color: activePalette === key ? C.accent : C.muted }}>{pal.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Тип графика */}
          {chartTypes && chartTypes.length > 1 && (
            <div>
              <div style={{ fontSize: 10, color: C.dim, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>Тип графика</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {chartTypes.map(t => (
                  <button key={t.value} onClick={() => handleChartType(t.value)}
                    style={btnStyle(currentChartType === t.value)}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
