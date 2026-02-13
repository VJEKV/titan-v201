import { useState, useEffect } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList, LineChart, Line } from 'recharts';
import { C, CHART_COLORS } from '../theme/arctic';
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

export default function Workplaces() {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const cs = useChartSettings();

  // Типы графиков
  const [donutType, setDonutType] = useState('donut');
  const [barType, setBarType] = useState('hbar');

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/workplaces', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, rm_data } = data;
  const overrun = rm_data.filter(d => d.dev > 0);
  const savings = rm_data.filter(d => d.dev < 0);
  const sortedByCount = [...rm_data].sort((a, b) => b.count - a.count).slice(0, 15);
  const colors = cs.paletteColors;
  const fsz = cs.fontSizes;
  const fontFamily = cs.font;

  /** Рендер бублика/пирога */
  const renderDonut = () => {
    const inner = donutType === 'pie' ? 0 : 140;
    return (
      <ResponsiveContainer width="100%" height={620}>
        <PieChart>
          <Pie data={rm_data.slice(0, 10)} dataKey="fact" nameKey="name" cx="50%" cy="50%"
            innerRadius={inner} outerRadius={230} paddingAngle={2}
            label={({ name, percent, cx: pcx, cy: pcy, midAngle, outerRadius: oR }) => {
              const RADIAN = Math.PI / 180;
              const radius = oR + 30;
              const x = pcx + radius * Math.cos(-midAngle * RADIAN);
              const y = pcy + radius * Math.sin(-midAngle * RADIAN);
              return (
                <text x={x} y={y} fill={C.text} fontSize={fsz.tick} fontFamily={fontFamily} textAnchor={x > pcx ? 'start' : 'end'} dominantBaseline="central">
                  {name || ''} {(percent*100).toFixed(0)}%
                </text>
              );
            }}
            labelLine={{ stroke: C.text, strokeWidth: 1 }}>
            {rm_data.slice(0, 10).map((_, i) => (
              <Cell key={i} fill={colors[i % colors.length]} stroke={C.bg} strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            itemStyle={{ color: C.text }} formatter={v => [`${fmtShort(v)} ₽`]} />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  /** Рендер бокового бар-чарта */
  const renderSideBar = () => {
    if (barType === 'vbar') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={sortedByCount}>
            <XAxis dataKey="name" tick={{ fill: C.muted, fontSize: fsz.tick - 1, fontFamily }} angle={-45} textAnchor="end" height={80} interval={0}
              tickFormatter={v => v.length > 18 ? v.slice(0,18)+'...' : v} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }} />
            <Bar dataKey="count" fill={C.accent} radius={[6,6,0,0]} name="Заказов">
              <LabelList dataKey="count" position="top" fill={C.muted} fontSize={fsz.label} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      );
    }
    return (
      <ResponsiveContainer width="100%" height={Math.max(400, sortedByCount.length * 40)}>
        <BarChart data={sortedByCount} layout="vertical">
          <XAxis type="number" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
          <YAxis type="category" dataKey="name" width={220} tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }}
            tickFormatter={v => v.length > 30 ? v.slice(0,30)+'...' : v} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            itemStyle={{ color: C.text }} />
          <Bar dataKey="count" fill={C.accent} radius={[0,6,6,0]} name="Заказов">
            <LabelList dataKey="count" position="right" fill={C.muted} fontSize={fsz.label} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div style={{ fontFamily }}>
      <SectionTitle sub="Кто сколько потратил, перерасход, количество заказов и ЕО">Аналитика по рабочим местам</SectionTitle>

      <KpiRow>
        <KpiCard title="РАБОЧИХ МЕСТ" value={kpi.rm_count} />
        <KpiCard title="ЗАКАЗОВ (Σ)" value={kpi.total_orders} />
        <KpiCard title="ФАКТ (Σ)" value={`${fmtShort(kpi.total_fact)} ₽`} />
        <KpiCard title="С ПЕРЕРАСХОДОМ" value={`${kpi.overrun_count} РМ`} color={C.warning} />
      </KpiRow>

      {/* Сводная — бублик */}
      <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>1. Сводная аналитика <ChartSettings chartId="wp-donut" chartTypes={[{value:'donut',label:'Бублик'},{value:'pie',label:'Пирог'}]} currentChartType={donutType} onChartTypeChange={setDonutType} /></span>}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 500px' }}>
            {renderDonut()}
            {/* Компактная легенда */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 8 }}>
              {rm_data.slice(0, 10).map((d, i) => {
                const clr = colors[i % colors.length];
                return (
                  <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8, lineHeight: 1.2 }}>
                    <div style={{ width: 12, height: 12, borderRadius: 2, background: clr, flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: C.text }}>{d.name}</span>
                    <span style={{ fontSize: 11, color: C.muted, marginLeft: 'auto', whiteSpace: 'nowrap' }}>{fmtShort(d.fact)} ₽</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div style={{ flex: '1 1 380px' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
              <ChartSettings chartId="wp-bar" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'}]} currentChartType={barType} onChartTypeChange={setBarType} />
            </div>
            {renderSideBar()}
          </div>
        </div>
      </Card>

      {/* Перерасход */}
      {overrun.length > 0 && (
        <Card title="2. РМ с перерасходом" borderColor={C.danger}>
          <HeatmapTable data={overrun.slice(0, 15)} />
        </Card>
      )}

      {/* Экономия */}
      {savings.length > 0 && (
        <Card title="3. РМ с экономией" borderColor={C.success}>
          <HeatmapTable data={savings.slice(0, 15)} />
        </Card>
      )}
    </div>
  );
}
