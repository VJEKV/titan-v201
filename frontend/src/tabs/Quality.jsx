import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { C } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import Card from '../components/Card';
import ChartSettings, { useChartSettings } from '../components/ChartSettings';
import DateFootnote from '../components/DateFootnote';

export default function Quality() {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const csBar = useChartSettings('q-bar');

  const [chartType, setChartType] = useState('hbar');

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/quality', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, fields } = data;
  const fieldsWithEmpty = fields.filter(f => f.empty > 0);
  const fsz = csBar.fontSizes;
  const fontFamily = csBar.font;

  const renderChart = () => {
    const qMainColor = csBar.paletteColors[1] || C.danger;
    if (chartType === 'vbar') {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={fieldsWithEmpty.slice(0, 30)}>
            <XAxis dataKey="name" tick={{ fill: C.muted, fontSize: fsz.tick - 1, fontFamily }} angle={-45} textAnchor="end" height={100} interval={0}
              tickFormatter={v => v.length > 18 ? v.slice(0,18)+'...' : v} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }}
              formatter={(v, name, props) => [`${v} (${props.payload.pct}%)`, 'Пустых']} />
            <Bar dataKey="empty" name="Пустых" fill={qMainColor} radius={[6,6,0,0]}
              label={{ position: 'top', fill: C.muted, fontSize: fsz.label - 1,
                formatter: (v) => {
                  const f = fieldsWithEmpty.find(x => x.empty === v);
                  return f ? `${f.pct}%` : '';
                }
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      );
    }
    // Horizontal bar (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={Math.max(400, fieldsWithEmpty.length * 28)}>
        <BarChart data={fieldsWithEmpty.slice(0, 30)} layout="vertical">
          <XAxis type="number" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
          <YAxis type="category" dataKey="name" width={220} tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }}
            formatter={(v, name, props) => [`${v} (${props.payload.pct}%)`, 'Пустых']} />
          <Bar dataKey="empty" name="Пустых"
            fill={qMainColor}
            radius={[0,4,4,0]}
            label={{ position: 'right', fill: C.muted, fontSize: fsz.label,
              formatter: (v) => {
                const f = fieldsWithEmpty.find(x => x.empty === v);
                return f ? `${f.pct}%` : '';
              }
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div style={{ fontFamily }}>
      <DateFootnote />
      <SectionTitle sub="Проверка полноты заполнения полей из справочника">
        Качество данных
      </SectionTitle>

      <KpiRow>
        <KpiCard title="ЗАКАЗОВ" value={kpi.total_rows} />
        <KpiCard title="ПОЛЕЙ" value={kpi.total_fields} />
        <KpiCard title="ПРОБЛЕМНЫХ (>30%)" value={kpi.problem_cols} color={kpi.problem_cols > 0 ? C.danger : C.success} />
        <KpiCard title="ЗАПОЛНЕННОСТЬ" value={`${kpi.fill_rate}%`} color={kpi.fill_rate > 80 ? C.success : C.warning} />
      </KpiRow>

      {data.date_stats && (() => {
        const ds = data.date_stats;
        const t = kpi.total_rows || 1;
        const pct = v => (v / t * 100).toFixed(1);
        const fmtN = v => Number(v).toLocaleString('ru-RU');
        const cats = [
          { label: 'Факт + План', color: C.success },
          { label: 'Только факт', color: '#ffffff' },
          { label: 'Только план', color: C.warning },
          { label: 'Нет дат', color: C.danger },
        ];
        const dRows = [
          { label: 'Начало', vals: [ds.start_both, ds.start_fact_only, ds.start_plan_only, ds.start_none] },
          { label: 'Конец', vals: [ds.end_both, ds.end_fact_only, ds.end_plan_only, ds.end_none] },
        ];
        const thS = { padding: '0 10px 6px', fontSize: 10, fontWeight: 600, textAlign: 'center', whiteSpace: 'nowrap' };
        const tdS = { padding: '4px 10px', textAlign: 'center', fontSize: 12 };
        const barH = 4;
        return (
          <Card title="Покрытие датами в заказах">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ ...thS, textAlign: 'left', minWidth: 70 }}></th>
                  {cats.map((c, i) => (
                    <th key={i} style={{ ...thS, color: c.color }}>{c.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dRows.map((row, ri) => (
                  <tr key={ri}>
                    <td style={{ ...tdS, textAlign: 'left', color: C.dim, fontSize: 11, fontWeight: 500 }}>{row.label}</td>
                    {row.vals.map((v, ci) => {
                      const p = pct(v);
                      return (
                        <td key={ci} style={tdS}>
                          <div style={{ fontWeight: 600, color: cats[ci].color }}>{fmtN(v)}</div>
                          <div style={{
                            width: '100%', height: barH, borderRadius: barH / 2,
                            background: C.border, marginTop: 3, overflow: 'hidden',
                          }}>
                            <div style={{
                              width: `${p}%`, height: '100%', borderRadius: barH / 2,
                              background: cats[ci].color, opacity: 0.7,
                            }} />
                          </div>
                          <div style={{ fontSize: 10, color: C.dim, marginTop: 2 }}>{p}%</div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        );
      })()}

      {/* График */}
      {fieldsWithEmpty.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>Незаполненность по полям <ChartSettings chartId="q-bar" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'}]} currentChartType={chartType} onChartTypeChange={setChartType} /></span>}>
          {renderChart()}
          <div style={{ display: 'flex', gap: 20, marginTop: 10, fontSize: 12 }}>
            <span style={{ color: C.danger }}>● {'>'}30%</span>
            <span style={{ color: C.warning }}>● 10-30%</span>
            <span style={{ color: C.success }}>● {'<'}10%</span>
          </div>
        </Card>
      )}

      {/* Таблица */}
      <Card title="Детализация по полям">
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                {['Наименование', 'Код поля', 'Заполнено', 'Пусто', '% пустых'].map(h => (
                  <th key={h} style={{ color: C.muted, fontSize: 12 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fields.map((f, i) => {
                const clr = f.pct > 30 ? C.danger : f.pct > 10 ? C.warning : C.success;
                return (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                    <td style={{ color: C.text, fontSize: 13 }}>{f.name}</td>
                    <td style={{ color: C.dim, fontSize: 12 }}>{f.code}</td>
                    <td style={{ color: C.success, fontSize: 13 }}>{f.filled}</td>
                    <td style={{ color: f.empty > 0 ? C.danger : C.muted, fontSize: 13 }}>{f.empty}</td>
                    <td style={{ color: clr, fontSize: 13, fontWeight: 600 }}>{f.pct}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
