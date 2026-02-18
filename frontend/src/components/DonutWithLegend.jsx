import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { C } from '../theme/arctic';

const RADIAN = Math.PI / 180;

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
  height = 450,
  innerRadius = 90,
  outerRadius = 155,
  fontSize = 11,
  fontFamily = 'Inter',
  minAngle = 35,
}) {
  if (!data || data.length === 0) return null;

  const total = data.reduce((s, d) => s + (d.value || 0), 0);

  return (
    <div style={{ display: 'flex', gap: 30, flexWrap: 'wrap', alignItems: 'center', width: '100%', justifyContent: 'center' }}>
      <div style={{ flex: '1 1 450px', minWidth: 350, maxWidth: 600 }}>
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
              label={({ name, percent, cx: pcx, cy: pcy, midAngle, outerRadius: oR, startAngle, endAngle }) => {
                const angle = Math.abs(endAngle - startAngle);
                if (angle < minAngle) return null;
                const radius = oR + 60;
                const x = pcx + radius * Math.cos(-midAngle * RADIAN);
                const y = pcy + radius * Math.sin(-midAngle * RADIAN);
                const pct = (percent * 100).toFixed(0);
                const val = fmtShort(data.find(d => d.name === name)?.value || 0);
                return (
                  <text x={x} y={y} fill="#e2e8f0" fontSize={fontSize} fontWeight={600} fontFamily={fontFamily}
                    textAnchor={x > pcx ? 'start' : 'end'} dominantBaseline="central">
                    <tspan x={x} dy="0">{name}</tspan>
                    <tspan x={x} dy="16">{pct}% | {val} \u20BD</tspan>
                  </text>
                );
              }}
              labelLine={{ stroke: '#64748b', strokeWidth: 1 }}
            >
              {data.map((_, i) => (
                <Cell key={`${chartId}-cell-${i}`} fill={colors[i % colors.length]} stroke={C.bg} strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }}
              formatter={v => [`${fmtShort(v)} \u20BD`]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div style={{ flex: '1 1 380px', minWidth: 300, maxWidth: 550, display: 'flex', flexDirection: 'column', gap: 5 }}>
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
                  {fmtNum(d.count)} \u0437\u0430\u043a.
                </span>
              )}
              <span style={{ fontSize: 11, color: C.muted, whiteSpace: 'nowrap', flexShrink: 0 }}>
                {fmtShort(d.value)} \u20BD ({d.pct != null ? d.pct : pct}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
