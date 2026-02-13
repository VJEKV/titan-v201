/**
 * ARCTIC DARK — Палитра цветов
 */
export const C = {
  // Фоны
  bg:       "#0f172a",
  surface:  "#1e293b",
  card:     "#273548",
  cardAlt:  "#1e2d42",

  // Акценты
  accent:   "#38bdf8",
  danger:   "#f43f5e",
  warning:  "#fbbf24",
  success:  "#34d399",
  purple:   "#a78bfa",
  orange:   "#fb923c",
  cyan:     "#22d3ee",

  // Текст
  text:     "#f1f5f9",
  muted:    "#94a3b8",
  dim:      "#64748b",

  // Бордеры
  border:   "#334155",
};

// Цвета методов
export const METHOD_COLORS = {
  "C1-M1": "#f43f5e",
  "C1-M6": "#fbbf24",
  "C1-M9": "#a78bfa",
  "C2-M2": "#fb923c",
  "NEW-9": "#22d3ee",
  "NEW-10": "#34d399",
};

// Цвета ABC
export const ABC_COLORS = {
  "A": "#f43f5e",
  "B": "#fbbf24",
  "C": "#34d399",
  "Н/Д": "#64748b",
};

// Recharts цвета
export const CHART_COLORS = [
  "#38bdf8", "#f43f5e", "#fbbf24", "#34d399",
  "#a78bfa", "#fb923c", "#22d3ee", "#f472b6",
  "#60a5fa", "#4ade80"
];

// Градиенты
export const GRADIENTS = {
  navbar: "linear-gradient(135deg, #1e293b 0%, #273548 100%)",
  card: "linear-gradient(145deg, #1e293b 0%, #273548 100%)",
};

// Палитры графиков (6 палитр)
export const CHART_PALETTES = {
  ice: {
    name: 'Ледяной',
    colors: ['#38bdf8', '#0ea5e9', '#0284c7', '#0369a1', '#075985', '#7dd3fc', '#bae6fd', '#e0f2fe', '#22d3ee', '#06b6d4'],
  },
  aurora: {
    name: 'Северное сияние',
    colors: ['#34d399', '#a78bfa', '#22d3ee', '#818cf8', '#6ee7b7', '#c084fc', '#2dd4bf', '#a5b4fc', '#4ade80', '#e879f9'],
  },
  steel: {
    name: 'Стальной',
    colors: ['#e2e8f0', '#cbd5e1', '#94a3b8', '#64748b', '#475569', '#f1f5f9', '#9ca3af', '#d1d5db', '#6b7280', '#374151'],
  },
  fire: {
    name: 'Огненная',
    colors: ['#ef4444', '#f97316', '#f59e0b', '#dc2626', '#ea580c', '#d97706', '#b91c1c', '#c2410c', '#fbbf24', '#fcd34d'],
  },
  ocean: {
    name: 'Океан',
    colors: ['#1e3a5f', '#0d9488', '#06b6d4', '#164e63', '#14b8a6', '#22d3ee', '#0c4a6e', '#2dd4bf', '#67e8f9', '#0e7490'],
  },
  neon: {
    name: 'Неон',
    colors: ['#ec4899', '#8b5cf6', '#3b82f6', '#06b6d4', '#d946ef', '#a78bfa', '#60a5fa', '#22d3ee', '#f472b6', '#c084fc'],
  },
};

// Пресеты размеров шрифта
export const FONT_SIZE_PRESETS = {
  S: { tick: 9, label: 10, legend: 10 },
  M: { tick: 11, label: 12, legend: 12 },
  L: { tick: 13, label: 14, legend: 14 },
};

// Шрифты
export const FONT_OPTIONS = ['Inter', 'JetBrains Mono', 'IBM Plex Sans'];

// Heatmap расчёт
export const heatBg = (val, absMax) => {
  if (!absMax || val === 0) return { bg: "transparent", tc: C.text };
  const i = Math.min(Math.abs(val) / absMax, 1);
  return val > 0
    ? { bg: `rgba(244,63,94,${0.06 + i * 0.2})`, tc: i > 0.2 ? "#fda4af" : "#fecdd3" }
    : { bg: `rgba(52,211,153,${0.06 + i * 0.2})`, tc: i > 0.2 ? "#6ee7b7" : "#a7f3d0" };
};
