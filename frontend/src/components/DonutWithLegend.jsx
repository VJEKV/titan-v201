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

/**
 * Универсальный компонент бублик + легенда.
 * @param {Object[]} data — массив { name, value, count, pct }
 * @param {string[]} colors — цвета секций
 * @param {string} chartId — id для ключей
 * @param {number} height — высота графика (380)
 * @param {number} innerRadius — внутренний радиус (90)
 * @param {number} outerRadius — внешний радиус (150)
 * @param {number} fontSize — размер шрифта подписей (12)
 * @param {string} fontFamily — шрифт (Inter)
 * @param {number} minAngle — минимальный угол для отображения подписи (25)
 * @param {number} maxLabelLen — макс. длина подписи (16)
 */
export default function DonutWithLegend({
  data,
  colors,
  chartId = 'donut',
  height = 420,
  innerRadius = 80,
  outerRadius = 145,
  fontSize = 13,
  fontFamily = 'Inter',
  minAngle = 30,
  maxLabelLen = 28,
}) {
  if (!data || data.length === 0) return null;

  return (
    <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'center' }}>
      {/* Бублик */}
      <div style={{ flex: '0 0 auto' }}>
        <ResponsiveContainer width={height} height={height}>
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
                const radius = oR + 50;
                const x = pcx + radius * Math.cos(-midAngle * RADIAN);
                const y = pcy + radius * Math.sin(-midAngle * RADIAN);
                const displayName = name && name.length > maxLabelLen ? name.slice(0, maxLabelLen) + '...' : (name || '');
                const pctLabel = percent != null ? ` ${(percent * 100).toFixed(0)}%` : '';
                return (
                  <text x={x} y={y} fill="#fff" fontSize={fontSize} fontWeight={600} fontFamily={fontFamily}
                    textAnchor={x > pcx ? 'start' : 'end'} dominantBaseline="central">
                    {displayName}{pctLabel}
                  </text>
                );
              }}
              labelLine={{ stroke: C.muted, strokeWidth: 1 }}
            >
              {data.map((_, i) => (
                <Cell key={`${chartId}-cell-${i}`} fill={colors[i % colors.length]} stroke={C.bg} strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }}
              formatter={v => [`${fmtShort(v)} ₽`]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Легенда */}
      <div style={{ flex: '0 1 420px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {data.map((d, i) => {
          const clr = colors[i % colors.length];
          return (
            <div key={`${chartId}-leg-${i}`} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '4px 10px', borderRadius: 6, minHeight: 34,
              background: `${clr}18`, borderLeft: `4px solid ${clr}`,
            }}>
              <div style={{ width: 12, height: 12, borderRadius: 2, background: clr, flexShrink: 0 }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: clr, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {d.name}
              </span>
              <span style={{ fontSize: 11, color: C.text, whiteSpace: 'nowrap' }}>
                {fmtNum(d.count)} зак.
              </span>
              <span style={{ fontSize: 10, color: C.muted, marginLeft: 'auto', whiteSpace: 'nowrap' }}>
                {fmtShort(d.value)} ₽ {d.pct != null ? `(${d.pct}%)` : ''}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
