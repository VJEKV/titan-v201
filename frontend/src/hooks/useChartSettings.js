import { useState, useEffect, useCallback } from 'react';
import { CHART_PALETTES, FONT_SIZE_PRESETS } from '../theme/arctic';

/**
 * Хук для индивидуальных настроек графика.
 * Каждый график имеет свои настройки, хранимые в localStorage.
 * @param {string} tabName — имя вкладки
 * @param {string} chartId — уникальный ID графика
 */
export function usePerChartSettings(tabName, chartId) {
  const key = `chart_${tabName}_${chartId}`;

  const getDefaults = () => ({
    palette: 'ice',
    height: 350,
    fontSize: 'M',
    showLabels: true,
    showLegend: true,
  });

  const readSettings = useCallback(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw) return { ...getDefaults(), ...JSON.parse(raw) };
    } catch {}
    return getDefaults();
  }, [key]);

  const [settings, setSettings] = useState(readSettings);

  // Слушаем события обновления
  useEffect(() => {
    const handler = () => setSettings(readSettings());
    window.addEventListener('chart-settings-changed', handler);
    window.addEventListener('storage', handler);
    return () => {
      window.removeEventListener('chart-settings-changed', handler);
      window.removeEventListener('storage', handler);
    };
  }, [readSettings]);

  const updateSettings = useCallback((patch) => {
    setSettings(prev => {
      const next = { ...prev, ...patch };
      localStorage.setItem(key, JSON.stringify(next));
      window.dispatchEvent(new Event('chart-settings-changed'));
      return next;
    });
  }, [key]);

  const colors = CHART_PALETTES[settings.palette]?.colors || CHART_PALETTES.ice.colors;
  const fontSizes = FONT_SIZE_PRESETS[settings.fontSize] || FONT_SIZE_PRESETS.M;

  return { settings, updateSettings, colors, fontSizes };
}
