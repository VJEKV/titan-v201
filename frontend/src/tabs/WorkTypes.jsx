import { useState, useEffect } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, LabelList, LineChart, Line } from 'recharts';
import { C } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import HeatmapTable from '../components/HeatmapTable';
import Card from '../components/Card';
import ChartSettings, { useChartSettings } from '../components/ChartSettings';

function fmtShort(v) {
  if (!v && v !== 0) return "0";
  const a = Math.abs(v), s = v >= 0 ? "" : "-";
  if (a >= 1e6) return `${s}${(a/1e6).toFixed(1)}М`;
  if (a >= 1e3) return `${s}${(a/1e3).toFixed(1)}К`;
  return `${s}${a.toFixed(0)}`;
}

function fmtNum(v) {
  if (!v && v !== 0) return '0';
  return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

/** Дедупликация по label */
function dedupeByLabel(arr) {
  const seen = new Set();
  return arr.filter(d => {
    if (seen.has(d.label)) return false;
    seen.add(d.label);
    return true;
  });
}

export default function WorkTypes() {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const csDonut = useChartSettings('wt-donut');
  const csBar = useChartSettings('wt-bar');
  const csMonthly = useChartSettings('wt-monthly');

  // Типы графиков
  const [donutType, setDonutType] = useState('donut');
  const [barType, setBarType] = useState('hbar');
  const [monthlyType, setMonthlyType] = useState('bar');

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/work-types', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, types_data, monthly } = data;
  const sortedByCount = [...types_data].sort((a, b) => b.count - a.count);
  const fsz = csDonut.fontSizes;
  const fontFamily = csDonut.font;

  /** Рендер бублика/пирога */
  const renderDonut = () => {
    const colors = csDonut.paletteColors;
    const inner = donutType === 'pie' ? 0 : 140;
    const RADIAN = Math.PI / 180;
    const showLabelsOnChart = types_data.length <= 5;
    return (
      <ResponsiveContainer width="100%" height={620}>
        <PieChart>
          <Pie data={types_data} dataKey="fact" nameKey="name" cx="50%" cy="50%"
            innerRadius={inner} outerRadius={230} paddingAngle={2}
            label={showLabelsOnChart ? ({ name, percent, cx: pcx, cy: pcy, midAngle, outerRadius: oR, startAngle, endAngle }) => {
              const angle = Math.abs(endAngle - startAngle);
              if (angle < 15) return null;
              const radius = oR + 30;
              const x = pcx + radius * Math.cos(-midAngle * RADIAN);
              const y = pcy + radius * Math.sin(-midAngle * RADIAN);
              const displayName = name && name.length > 20 ? name.slice(0, 20) + '...' : (name || '');
              return (
                <text x={x} y={y} fill={C.text} fontSize={fsz.tick} fontFamily={fontFamily} textAnchor={x > pcx ? 'start' : 'end'} dominantBaseline="central">
                  {displayName} {(percent*100).toFixed(0)}%
                </text>
              );
            } : false}
            labelLine={showLabelsOnChart ? { stroke: C.muted, strokeWidth: 1 } : false}>
            {types_data.map((_, i) => (
              <Cell key={i} fill={colors[i % colors.length]} stroke={C.bg} strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            itemStyle={{ color: C.text }} formatter={v => [`${fmtShort(v)} ₽`, 'Факт']} />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  /** Рендер бокового бар-чарта */
  const renderSideBar = () => {
    const barMainColor = csBar.paletteColors[0];
    if (barType === 'vbar') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={sortedByCount}>
            <XAxis dataKey="name" tick={{ fill: C.muted, fontSize: fsz.tick - 1, fontFamily }} angle={-45} textAnchor="end" height={80} interval={0}
              tickFormatter={v => v.length > 18 ? v.slice(0,18)+'...' : v} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }} />
            <Bar dataKey="count" fill={barMainColor} radius={[6,6,0,0]} name="Заказов">
              <LabelList dataKey="count" position="top" fill={C.muted} fontSize={fsz.label} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      );
    }
    // Horizontal bar (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={Math.max(350, sortedByCount.length * 40)}>
        <BarChart data={sortedByCount} layout="vertical">
          <XAxis type="number" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
          <YAxis type="category" dataKey="name" width={180} tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }}
            tickFormatter={v => v.length > 25 ? v.slice(0,25)+'...' : v} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            itemStyle={{ color: C.text }} />
          <Bar dataKey="count" fill={barMainColor} radius={[0,6,6,0]} name="Заказов">
            <LabelList dataKey="count" position="right" fill={C.muted} fontSize={fsz.label} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div style={{ fontFamily }}>
      <SectionTitle sub="Плановые vs внеплановые, стоимость по видам">Анализ по видам работ</SectionTitle>

      <KpiRow>
        <KpiCard title="ВИДОВ РАБОТ" value={kpi.types_count} />
        <KpiCard title="ЗАКАЗОВ (Σ)" value={kpi.total_orders} />
        <KpiCard title="ВНЕПЛАНОВЫЕ" value={`${kpi.unplanned_count} зак.`} sub={`${kpi.unplanned_pct}%`} color={C.danger} />
        <KpiCard title="ОТКЛОНЕНИЕ (Σ)" value={`${fmtShort(kpi.total_dev)} ₽`} color={kpi.total_dev > 0 ? C.danger : C.success} />
      </KpiRow>

      {/* Heatmap */}
      <Card title="1. Виды работ: План, Факт, Отклонение">
        <HeatmapTable data={types_data} />
      </Card>

      {/* Donut + Bars */}
      <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>2. Сводная аналитика <ChartSettings chartId="wt-donut" chartTypes={[{value:'donut',label:'Бублик'},{value:'pie',label:'Пирог'}]} currentChartType={donutType} onChartTypeChange={setDonutType} /></span>}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 500px' }}>
            {renderDonut()}
            {/* Компактная легенда */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 8 }}>
              {types_data.map((d, i) => {
                const clr = csDonut.paletteColors[i % csDonut.paletteColors.length];
                return (
                  <div key={d.name} style={{
                    display: 'flex', alignItems: 'center', gap: 8, height: 30, padding: '4px 8px',
                    borderRadius: 4, background: `${clr}10`, borderLeft: `3px solid ${clr}`,
                  }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: clr, flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: C.text, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
                    <span style={{ fontSize: 11, color: C.muted, whiteSpace: 'nowrap' }}>{fmtNum(d.count)} зак.</span>
                    <span style={{ fontSize: 11, color: clr, whiteSpace: 'nowrap', fontWeight: 600 }}>{fmtShort(d.fact)} ₽</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div style={{ flex: '1 1 380px' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
              <ChartSettings chartId="wt-bar" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'}]} currentChartType={barType} onChartTypeChange={setBarType} />
            </div>
            {renderSideBar()}
          </div>
        </div>
      </Card>

      {/* Помесячно */}
      {monthly.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>3. Виды работ по месяцам <ChartSettings chartId="wt-monthly" chartTypes={[{value:'bar',label:'Столбцы'},{value:'line',label:'Линия'}]} currentChartType={monthlyType} onChartTypeChange={setMonthlyType} /></span>}>
          {monthlyType === 'line' ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={dedupeByLabel(monthly[0]?.data?.map((d, i) => {
                const item = { label: d.label };
                monthly.forEach(m => { item[m.name] = m.data[i]?.count || 0; });
                return item;
              }) || [])}>
                <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick - 1, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
                <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
                <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
                  itemStyle={{ color: C.text }} />
                <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend - 2 }}>{v.length > 25 ? v.slice(0,25)+'...' : v}</span>} />
                {monthly.map((m, i) => {
                  const monthColors = csMonthly.paletteColors;
                  return <Line key={m.name} dataKey={m.name} stroke={monthColors[i % monthColors.length]} strokeWidth={2} dot={{ r: 3 }} />;
                })}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={dedupeByLabel(monthly[0]?.data?.map((d, i) => {
                const item = { label: d.label };
                monthly.forEach(m => { item[m.name] = m.data[i]?.count || 0; });
                return item;
              }) || [])}>
                <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick - 1, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
                <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
                <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
                  itemStyle={{ color: C.text }} />
                <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend - 2 }}>{v.length > 25 ? v.slice(0,25)+'...' : v}</span>} />
                {monthly.map((m, i) => {
                  const monthColors = csMonthly.paletteColors;
                  return <Bar key={m.name} dataKey={m.name} stackId="a" fill={monthColors[i % monthColors.length]} radius={[4,4,0,0]} />;
                })}
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      )}
    </div>
  );
}
