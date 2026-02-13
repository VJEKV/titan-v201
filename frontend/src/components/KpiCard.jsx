import { C, GRADIENTS } from '../theme/arctic';

/**
 * KPI карточка с заголовком, значением и опциональным подзначением
 */
export default function KpiCard({ title, value, sub, color, icon }) {
  return (
    <div style={{
      background: GRADIENTS.card,
      borderTop: `3px solid ${color || C.accent}`,
      borderRadius: 10,
      padding: '16px 20px',
      minWidth: 160,
      flex: 1,
    }}>
      <div style={{ fontSize: 11, color: C.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
        {icon && <span style={{ marginRight: 6 }}>{icon}</span>}
        {title}
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || C.text }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: color || C.muted, marginTop: 4 }}>
          {sub}
        </div>
      )}
    </div>
  );
}
