import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { C } from '../theme/arctic';

function fmtShort(v) {
  if (!v && v !== 0) return "0";
  const a = Math.abs(v), s = v >= 0 ? "" : "-";
  if (a >= 1e9) return `${s}${(a/1e9).toFixed(1)}Млрд`;
  if (a >= 1e6) return `${s}${(a/1e6).toFixed(1)}М`;
  if (a >= 1e3) return `${s}${(a/1e3).toFixed(1)}К`;
  return `${s}${a.toFixed(0)}`;
}

function fmtNum(v) {
  if (!v && v !== 0) return '0';
  return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

export default function DonutWithLegend({
  data,
  colors,
  chartId = 'donut',
  height = 340,
  innerRadius = 70,
  outerRadius = 125,
  fontSize = 11,
  fontFamily = 'Inter',
}) {
  if (!data || data.length === 0) return null;

  const total = data.reduce((s, d) => s + (d.value || 0), 0);

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center', width: '100%', justifyContent: 'center' }}>
      <div style={{ flex: '0 0 300px', minWidth: 260, maxWidth: 340 }}>
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              paddingAngle={2}
              label={false}
              labelLine={false}
            >
              {data.map((_, i) => (
                <Cell key={`${chartId}-cell-${i}`} fill={colors[i % colors.length]} stroke={C.bg} strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload[0]) return null;
                const d = payload[0].payload;
                const clr = payload[0].payload.fill || colors[data.indexOf(d)] || C.accent;
                const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0';
                return (
                  <div style={{
                    background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8,
                    padding: '10px 14px', fontFamily, minWidth: 180,
                  }}>
                    <div style={{ color: clr, fontWeight: 700, fontSize: 13, marginBottom: 6 }}>{d.name}</div>
                    <div style={{ color: C.text, fontSize: 12, marginBottom: 3 }}>Сумма: <b>{fmtNum(d.value)} ₽</b></div>
                    <div style={{ color: C.text, fontSize: 12, marginBottom: 3 }}>Доля: <b>{d.pct != null ? d.pct : pct}%</b></div>
                    {d.count != null && (
                      <div style={{ color: C.text, fontSize: 12 }}>Заказов: <b>{fmtNum(d.count)}</b></div>
                    )}
                  </div>
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div style={{ flex: '1 1 380px', minWidth: 300, maxWidth: 600, display: 'flex', flexDirection: 'column', gap: 5 }}>
        {data.map((d, i) => {
          const clr = colors[i % colors.length];
          const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0';
          return (
            <div key={`${chartId}-leg-${i}`} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '5px 12px', borderRadius: 6, minHeight: 34,
              background: `${clr}18`, borderLeft: `4px solid ${clr}`,
            }}>
              <div style={{ width: 12, height: 12, borderRadius: 2, background: clr, flexShrink: 0 }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: clr, flex: '1 1 auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                title={d.name}>
                {d.name}
              </span>
              {d.count != null && (
                <span style={{ fontSize: 12, color: C.text, whiteSpace: 'nowrap', flexShrink: 0 }}>
                  {fmtNum(d.count)} зак.
                </span>
              )}
              <span style={{ fontSize: 11, color: C.muted, whiteSpace: 'nowrap', flexShrink: 0 }}>
                {fmtShort(d.value)} ₽ ({d.pct != null ? d.pct : pct}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
