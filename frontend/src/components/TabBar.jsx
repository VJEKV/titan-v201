import { C } from '../theme/arctic';

/**
 * Неоновые цвета для каждой вкладки
 */
const TABS = [
  { id: 'finance',    label: 'Финансы',          icon: '💰', neon: '#f59e0b' },
  { id: 'equipment',  label: 'Оборудование',     icon: '⚙️', neon: '#06b6d4' },
  { id: 'timeline',   label: 'Сроки',            icon: '📅', neon: '#ef4444' },
  { id: 'work-types', label: 'Виды работ',       icon: '🔧', neon: '#8b5cf6' },
  { id: 'planners',   label: 'Плановики',        icon: '👥', neon: '#10b981' },
  { id: 'workplaces', label: 'Раб.места',        icon: '🏗️', neon: '#ec4899' },
  { id: 'risks',      label: 'Приоритеты',       icon: '⚠️', neon: '#f97316' },
  { id: 'quality',    label: 'Качество данных',   icon: '📊', neon: '#3b82f6' },
  { id: 'orders',     label: 'Просмотр заказов',  icon: '📋', neon: '#6366f1' },
];

/**
 * Вспомогательная: hex → r,g,b строка для rgba()
 */
function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r},${g},${b}`;
}

/**
 * Панель вкладок — multi-color neon, на всю ширину
 */
export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div style={{
      display: 'flex',
      gap: 6,
      background: 'rgba(15,23,42,0.95)',
      padding: '8px 12px',
      borderRadius: 16,
      marginBottom: 16,
      border: '1px solid rgba(148,163,184,0.15)',
    }}>
      {TABS.map(tab => {
        const active = tab.id === activeTab;
        const nc = tab.neon;
        const rgb = hexToRgb(nc);

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            onMouseEnter={e => {
              if (!active) {
                e.currentTarget.style.color = '#e2e8f0';
                e.currentTarget.style.borderColor = `${nc}55`;
                e.currentTarget.style.background = `rgba(${rgb},0.06)`;
              }
            }}
            onMouseLeave={e => {
              if (!active) {
                e.currentTarget.style.color = '#94a3b8';
                e.currentTarget.style.borderColor = 'rgba(100,116,139,0.25)';
                e.currentTarget.style.background = 'transparent';
              }
            }}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '12px 10px',
              borderRadius: 12,
              cursor: 'pointer',
              fontSize: 15,
              whiteSpace: 'nowrap',
              transition: 'all 0.2s',
              ...(active
                ? {
                    border: `1.5px solid ${nc}`,
                    background: `linear-gradient(135deg, ${nc}33, ${nc}11)`,
                    color: '#fff',
                    fontWeight: 700,
                    boxShadow: `0 0 12px ${nc}66, 0 0 25px ${nc}22, inset 0 0 12px ${nc}15`,
                    textShadow: `0 0 8px ${nc}88`,
                    letterSpacing: 0.3,
                  }
                : {
                    border: '1px solid rgba(100,116,139,0.25)',
                    background: 'transparent',
                    color: '#94a3b8',
                    fontWeight: 400,
                    boxShadow: 'none',
                    textShadow: 'none',
                    letterSpacing: 0,
                  }),
            }}
          >
            <span style={{ fontSize: 17, marginRight: 6, lineHeight: 1 }}>{tab.icon}</span>
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
