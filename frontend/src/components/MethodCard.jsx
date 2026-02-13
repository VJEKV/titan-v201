import { C, GRADIENTS, METHOD_COLORS } from '../theme/arctic';

/**
 * Карточка метода с donut SVG — единый размер, увеличенный донат
 */
export default function MethodCard({ name, desc, count, total, sum, color, threshold, icon, orders_without_eo }) {
  const pct = total > 0 ? (count / total * 100) : 0;
  const methodKey = name.split(':')[0];
  const clr = color || METHOD_COLORS[methodKey] || C.accent;

  // SVG Donut — увеличенный
  const r = 40;
  const circ = 2 * Math.PI * r;
  const dashOffset = circ - (pct / 100) * circ;

  function fmtShort(val) {
    if (!val) return "0";
    const abs = Math.abs(val);
    if (abs >= 1e6) return `${(abs / 1e6).toFixed(1)}М`;
    if (abs >= 1e3) return `${(abs / 1e3).toFixed(1)}К`;
    return abs.toFixed(0);
  }

  return (
    <div style={{
      background: GRADIENTS.card,
      borderLeft: `5px solid ${clr}`,
      borderRadius: 10,
      padding: '16px 20px',
      display: 'flex',
      gap: 16,
      alignItems: 'center',
      border: `1px solid ${C.border}`,
      minHeight: 110,
      boxSizing: 'border-box',
    }}>
      {/* Donut — увеличенный */}
      <svg width={100} height={100} viewBox="0 0 100 100" style={{ flexShrink: 0 }}>
        <circle cx="50" cy="50" r={r} fill="none" stroke={C.border} strokeWidth="7" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={clr} strokeWidth="7"
          strokeDasharray={circ} strokeDashoffset={dashOffset}
          strokeLinecap="round" transform="rotate(-90 50 50)" />
        <text x="50" y="46" textAnchor="middle" fill={clr} fontSize="16" fontWeight="700">
          {count}
        </text>
        <text x="50" y="62" textAnchor="middle" fill={C.muted} fontSize="10">
          {pct.toFixed(1)}%
        </text>
      </svg>

      {/* Инфо */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: clr, marginBottom: 4 }}>
          {icon} {name}
        </div>
        <div style={{ fontSize: 12, color: C.muted, marginBottom: 6 }}>{desc}</div>
        <div style={{ fontSize: 12, color: C.dim }}>
          {fmtShort(sum)} ₽ | Порог: {threshold}
        </div>
        {orders_without_eo != null && orders_without_eo > 0 && (
          <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>
            Заказов без ЕО: {orders_without_eo.toLocaleString('ru-RU')} (не учтены)
          </div>
        )}
      </div>
    </div>
  );
}
