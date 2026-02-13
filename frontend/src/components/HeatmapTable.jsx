import { C, heatBg } from '../theme/arctic';

/**
 * Heatmap-таблица с RGB-градиентным фоном строк
 */

function fmtShort(val) {
  if (!val && val !== 0) return "0";
  const abs = Math.abs(val);
  const sign = val >= 0 ? "" : "-";
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(1)}Млрд`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(1)}М`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(1)}К`;
  return `${sign}${abs.toFixed(0)}`;
}

export default function HeatmapTable({ data, nameKey = "name" }) {
  if (!data || data.length === 0) return <p style={{ color: C.muted }}>Нет данных</p>;

  const absMax = Math.max(...data.map(d => Math.abs(d.dev || 0)), 1);

  return (
    <div style={{ overflowX: 'auto', borderRadius: 8, border: `1px solid ${C.border}` }}>
      <table>
        <thead>
          <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
            <th style={{ color: C.muted, fontSize: 12 }}>Наименование</th>
            <th style={{ color: C.muted, fontSize: 12, textAlign: 'right' }}>План</th>
            <th style={{ color: C.muted, fontSize: 12, textAlign: 'right' }}>Факт</th>
            <th style={{ color: C.muted, fontSize: 12, textAlign: 'right' }}>Отклонение</th>
            <th style={{ color: C.muted, fontSize: 12, textAlign: 'center' }}>Заказов</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => {
            const { bg, tc } = heatBg(row.dev || 0, absMax);
            const sign = row.dev > 0 ? "+" : "";
            return (
              <tr key={i} style={{ background: bg, borderBottom: `1px solid ${C.border}33` }}>
                <td style={{ color: C.text, fontSize: 13, maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    title={row[nameKey]}>
                  {i + 1}. {row[nameKey]}
                </td>
                <td style={{ color: '#e0e0e0', textAlign: 'right', fontSize: 13 }}>{fmtShort(row.plan)} ₽</td>
                <td style={{ color: '#e0e0e0', textAlign: 'right', fontSize: 13 }}>{fmtShort(row.fact)} ₽</td>
                <td style={{ color: tc, textAlign: 'right', fontSize: 14, fontWeight: 600 }}>{sign}{fmtShort(row.dev)} ₽</td>
                <td style={{ color: '#ccc', textAlign: 'center', fontSize: 13 }}>{row.count}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
