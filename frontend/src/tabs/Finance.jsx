import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, LineChart, Line, ReferenceLine, LabelList, Legend } from 'recharts';
import { C } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet, apiDownload } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import HeatmapTable from '../components/HeatmapTable';
import Card from '../components/Card';
import ChartSettings, { useChartSettings } from '../components/ChartSettings';

function fmtShort(v) {
  if (!v && v !== 0) return "0";
  const a = Math.abs(v), s = v >= 0 ? "" : "-";
  if (a >= 1e9) return `${s}${(a/1e9).toFixed(1)}Млрд`;
  if (a >= 1e6) return `${s}${(a/1e6).toFixed(1)}М`;
  if (a >= 1e3) return `${s}${(a/1e3).toFixed(1)}К`;
  return `${s}${a.toFixed(0)}`;
}

const fmt = v => v ? `${fmtShort(v)} ₽` : '0 ₽';

/** Рендер подписи на столбце */
const renderBarLabel = (props) => {
  const { x, y, width, value } = props;
  if (!value) return null;
  return (
    <text x={x + width / 2} y={y - 5} textAnchor="middle" fill={C.muted} fontSize={10}>
      {fmtShort(value)}
    </text>
  );
};

/** Дедупликация месяцев — оставляем только уникальные label */
function dedupeByLabel(arr) {
  const seen = new Set();
  return arr.filter(d => {
    if (seen.has(d.label)) return false;
    seen.add(d.label);
    return true;
  });
}

/** Сокращённый формат месяца */
const shortMonth = (label) => {
  if (!label) return '';
  return label;
};

export default function Finance() {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const csMain = useChartSettings('fin-monthly');
  const csPareto = useChartSettings('fin-pareto');

  // Типы графиков
  const [monthlyChartType, setMonthlyChartType] = useState('bar');
  const [paretoChartType, setParetoChartType] = useState('area');

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/finance', { session_id: sessionId, filters, thresholds })
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, monthly: rawMonthly, ceh_data, tm_data, pareto, pareto_orders, pareto_stats } = data;
  const monthly = dedupeByLabel(rawMonthly || []);
  const fs = csMain.fontSizes;
  const fontFamily = csMain.font;

  /** Кнопка выгрузки таблицы в Excel */
  const ExcelBtn = ({ tableData, title }) => {
    const handleExport = () => {
      const header = ['Наименование', 'План', 'Факт', 'Отклонение', 'Заказов'];
      const rows = tableData.map(r => [r.name, r.plan, r.fact, r.dev, r.count]);
      const csv = [header, ...rows].map(r => r.join('\t')).join('\n');
      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${title}_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    };
    return (
      <button onClick={handleExport} style={{
        padding: '6px 14px', background: C.bg, border: `1px solid ${C.border}`,
        borderRadius: 6, color: C.accent, cursor: 'pointer', fontSize: 12, marginBottom: 8,
      }}>
        Выгрузить в Excel
      </button>
    );
  };

  /** Рендер помесячного графика */
  const renderMonthlyChart = () => {
    if (monthlyChartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={monthly}>
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} tickFormatter={shortMonth} />
            <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={fmtShort} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              formatter={v => [fmt(v)]} labelStyle={{ color: C.accent }} itemStyle={{ color: C.text }} />
            <Legend wrapperStyle={{ color: C.muted, fontSize: fs.legend, paddingTop: 8 }}
              formatter={v => <span style={{ color: C.muted }}>{v}</span>} />
            <Line dataKey="plan" stroke={csMain.paletteColors[0]} strokeWidth={2} dot={{ r: 4 }} name="План" />
            <Line dataKey="fact" stroke={csMain.paletteColors[1]} strokeWidth={2} dot={{ r: 4 }} name="Факт" />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    if (monthlyChartType === 'area') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <AreaChart data={monthly}>
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} tickFormatter={shortMonth} />
            <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={fmtShort} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              formatter={v => [fmt(v)]} labelStyle={{ color: C.accent }} itemStyle={{ color: C.text }} />
            <Legend wrapperStyle={{ color: C.muted, fontSize: fs.legend, paddingTop: 8 }}
              formatter={v => <span style={{ color: C.muted }}>{v}</span>} />
            <Area type="monotone" dataKey="plan" stroke={csMain.paletteColors[0]} fill={`${csMain.paletteColors[0]}20`} strokeWidth={2} name="План" />
            <Area type="monotone" dataKey="fact" stroke={csMain.paletteColors[1]} fill={`${csMain.paletteColors[1]}20`} strokeWidth={2} name="Факт" />
          </AreaChart>
        </ResponsiveContainer>
      );
    }
    // Bar (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={380}>
        <BarChart data={monthly} barCategoryGap="20%">
          <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} tickFormatter={shortMonth} />
          <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={fmtShort} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            formatter={v => [fmt(v)]} labelStyle={{ color: C.accent }} itemStyle={{ color: C.text }} />
          <Legend wrapperStyle={{ color: C.muted, fontSize: fs.legend, paddingTop: 8 }}
            formatter={v => <span style={{ color: C.muted }}>{v}</span>} />
          <Bar dataKey="plan" fill={csMain.paletteColors[0]} radius={[4,4,0,0]} name="План">
            <LabelList dataKey="plan" content={renderBarLabel} />
          </Bar>
          <Bar dataKey="fact" fill={csMain.paletteColors[1]} radius={[4,4,0,0]} name="Факт">
            <LabelList dataKey="fact" content={renderBarLabel} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };

  /** Рендер парето */
  const renderParetoChart = () => {
    if (paretoChartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={pareto}>
            <XAxis dataKey="order_pct" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={v => `${v}%`} />
            <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={v => `${v}%`} domain={[0, 105]} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }}
              formatter={(v, name) => [`${v}%`, name === 'cum_pct' ? 'Кумул. затраты' : name]}
              labelFormatter={v => `${v}% заказов`} />
            <ReferenceLine y={80} stroke={C.danger} strokeDasharray="5 5" label={{ value: '80%', fill: C.danger, fontSize: fs.label }} />
            <ReferenceLine x={20} stroke={C.warning} strokeDasharray="5 5" label={{ value: '20%', fill: C.warning, fontSize: fs.label, position: 'top' }} />
            <Line type="monotone" dataKey="cum_pct" stroke={C.accent} strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    // Area (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={350}>
        <AreaChart data={pareto}>
          <XAxis dataKey="order_pct" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={v => `${v}%`} />
          <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={v => `${v}%`} domain={[0, 105]} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }}
            formatter={(v, name) => [`${v}%`, name === 'cum_pct' ? 'Кумул. затраты' : name]}
            labelFormatter={v => `${v}% заказов`} />
          <ReferenceLine y={80} stroke={C.danger} strokeDasharray="5 5" label={{ value: '80%', fill: C.danger, fontSize: fs.label }} />
          <ReferenceLine x={20} stroke={C.warning} strokeDasharray="5 5" label={{ value: '20%', fill: C.warning, fontSize: fs.label, position: 'top' }} />
          <Area type="monotone" dataKey="cum_pct" stroke={C.accent} fill={`${C.accent}20`} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div style={{ fontFamily }}>
      <SectionTitle sub="Суммарная стоимость, отклонения по цехам и ТМ, ABC">
        Финансовый анализ
      </SectionTitle>

      <KpiRow>
        <KpiCard title="ПЛАН (Σ)" value={fmt(kpi.plan)} />
        <KpiCard title="ФАКТ (Σ)" value={fmt(kpi.fact)} />
        <KpiCard title="ОТКЛОНЕНИЕ" value={fmt(kpi.dev)}
          sub={`${kpi.dev_pct > 0 ? '+' : ''}${kpi.dev_pct}%`}
          color={kpi.dev > 0 ? C.danger : C.success} />
        <KpiCard title="С ПЕРЕРАСХОДОМ" value={`${kpi.overrun_count} зак.`} color={C.warning} />
      </KpiRow>

      {/* 1. Помесячно — План и Факт */}
      {monthly.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>1. Плановая и фактическая стоимость по месяцам <ChartSettings chartId="fin-monthly" chartTypes={[{value:'bar',label:'Столбцы'},{value:'line',label:'Линия'},{value:'area',label:'Область'}]} currentChartType={monthlyChartType} onChartTypeChange={setMonthlyChartType} /></span>}>
          {renderMonthlyChart()}
        </Card>
      )}

      {/* 2. Цеха */}
      {ceh_data.length > 0 && (
        <Card title="2. Отклонения по цехам (Факт − План)">
          <ExcelBtn tableData={ceh_data} title="Отклонения_по_цехам" />
          <HeatmapTable data={ceh_data} />
        </Card>
      )}

      {/* 3. ТМ */}
      {tm_data.length > 0 && (
        <Card title="3. Отклонения по ТМ (Факт − План)">
          <ExcelBtn tableData={tm_data} title="Отклонения_по_ТМ" />
          <HeatmapTable data={tm_data} />
        </Card>
      )}

      {/* 4. Парето 80/20 */}
      {pareto.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>4. Парето: правило 80/20 — концентрация затрат <ChartSettings chartId="fin-pareto" chartTypes={[{value:'area',label:'Область'},{value:'line',label:'Линия'}]} currentChartType={paretoChartType} onChartTypeChange={setParetoChartType} /></span>}>
          {pareto_stats && (
            <div style={{ marginBottom: 12, padding: '10px 14px', borderRadius: 8, background: `${C.danger}10`, borderLeft: `4px solid ${C.danger}` }}>
              <span style={{ color: C.text, fontSize: 14 }}>
                <strong style={{ color: C.danger }}>{pareto_stats.orders_pct}%</strong> заказов ({pareto_stats.orders_80pct} из {pareto_stats.total_orders}) формируют <strong style={{ color: C.danger }}>80%</strong> всех затрат
              </span>
            </div>
          )}
          {renderParetoChart()}

          {/* Детализация заказов 80% */}
          {pareto_orders && pareto_orders.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: C.accent }}>
                  Заказы, формирующие 80% затрат
                </div>
                <ExcelBtn tableData={pareto_orders.map(r => ({
                  name: r.id, plan: r.plan, fact: r.fact, dev: r.fact - r.plan, count: 1
                }))} title="Парето_80_20" />
              </div>
              <div style={{ overflowX: 'auto', borderRadius: 8, border: `1px solid ${C.border}` }}>
                <table>
                  <thead>
                    <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                      {['#', 'ID', 'Текст', 'Код ЕО', 'Наим. ЕО', 'Вид', 'ТМ', 'План', 'Факт', 'Кумул. %'].map(h => (
                        <th key={h} style={{ color: C.muted, fontSize: 11, whiteSpace: 'nowrap', padding: '8px 10px' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {pareto_orders.slice(0, 50).map((r, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                        <td style={{ color: C.dim, fontSize: 12, padding: '6px 10px' }}>{i + 1}</td>
                        <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px' }}>{r.id}</td>
                        <td style={{ color: C.text, fontSize: 12, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px 10px' }}
                          title={r.text}>{r.text}</td>
                        <td style={{ color: C.muted, fontSize: 12, maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px 10px' }}
                          title={r.equipment_code || ''}>{r.equipment_code || '—'}</td>
                        <td style={{ color: C.muted, fontSize: 12, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px 10px' }}
                          title={r.equipment_name || ''}>{r.equipment_name || '—'}</td>
                        <td style={{ color: C.muted, fontSize: 12, padding: '6px 10px' }}>{r.vid}</td>
                        <td style={{ color: C.muted, fontSize: 12, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px 10px' }}
                          title={r.tm}>{r.tm}</td>
                        <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.plan)} ₽</td>
                        <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.fact)} ₽</td>
                        <td style={{ color: r.cum_pct >= 80 ? C.danger : C.warning, fontSize: 12, textAlign: 'center', fontWeight: 600, padding: '6px 10px' }}>
                          {r.cum_pct}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
