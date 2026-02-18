import { C } from '../theme/arctic';

const TABS = [
  { id: 'finance', label: 'Финансы', icon: '💰' },
  { id: 'equipment', label: 'Оборудование', icon: '⚙️' },
  { id: 'timeline', label: 'Сроки', icon: '📅' },
  { id: 'work-types', label: 'Виды работ', icon: '🔧' },
  { id: 'planners', label: 'Плановики', icon: '👥' },
  { id: 'workplaces', label: 'Раб.места', icon: '🏗️' },
  { id: 'risks', label: 'Приоритеты', icon: '⚠️' },
  { id: 'quality', label: 'C4 Качество', icon: '📊' },
  { id: 'orders', label: 'Заказы', icon: '📋' },
];

/**
 * Панель вкладок
 */
export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div style={{
      display: 'flex',
      gap: 2,
      overflowX: 'auto',
      background: C.surface,
      padding: '4px 8px',
      borderRadius: 8,
      marginBottom: 16,
    }}>
      {TABS.map(tab => {
        const active = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            style={{
              padding: '12px 20px',
              borderRadius: 6,
              border: 'none',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: active ? 600 : 400,
              color: active ? C.accent : C.muted,
              background: active ? C.card : 'transparent',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        );
      })}
    </div>
  );
}
