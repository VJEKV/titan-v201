import { C } from '../theme/arctic';

const TABS = [
  { id: 'finance', label: 'Финансы', icon: '💰' },
  { id: 'equipment', label: 'Оборудование', icon: '⚙️' },
  { id: 'timeline', label: 'Сроки', icon: '📅' },
  { id: 'work-types', label: 'Виды работ', icon: '🔧' },
  { id: 'planners', label: 'Плановики', icon: '👥' },
  { id: 'workplaces', label: 'Раб.места', icon: '🏗️' },
  { id: 'risks', label: 'Приоритеты', icon: '⚠️' },
  { id: 'quality', label: 'Качество данных', icon: '📊' },
  { id: 'orders', label: 'Просмотр заказов', icon: '📋' },
];

/**
 * Панель вкладок — основная навигация
 */
export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div style={{
      display: 'flex',
      gap: 4,
      overflowX: 'auto',
      background: 'rgba(30,41,59,0.5)',
      padding: '8px 10px',
      borderRadius: 12,
      marginBottom: 16,
      border: `1px solid ${C.border}`,
    }}>
      {TABS.map(tab => {
        const active = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            onMouseEnter={e => {
              if (!active) {
                e.currentTarget.style.borderColor = C.accent;
                e.currentTarget.style.background = 'rgba(56,189,248,0.07)';
              }
            }}
            onMouseLeave={e => {
              if (!active) {
                e.currentTarget.style.borderColor = '#475569';
                e.currentTarget.style.background = 'transparent';
              }
            }}
            style={{
              padding: '10px 20px',
              borderRadius: 8,
              border: active ? `2px solid ${C.accent}` : '1px solid #475569',
              cursor: 'pointer',
              fontSize: 15,
              fontWeight: active ? 700 : 400,
              color: active ? '#fff' : C.muted,
              background: active
                ? `linear-gradient(145deg, ${C.card} 0%, rgba(56,189,248,0.15) 100%)`
                : 'transparent',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s',
              letterSpacing: active ? 0.3 : 0,
            }}
          >
            <span style={{ fontSize: 17, marginRight: 6, verticalAlign: 'middle' }}>{tab.icon}</span>
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
