import { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, LabelList } from 'recharts';
import { C, CHART_COLORS } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import Card from '../components/Card';
import ChartSettings, { useChartSettings } from '../components/ChartSettings';

function fmtShort(v) {
  if (!v && v !== 0) return "0";
  const a = Math.abs(v), s = v >= 0 ? "" : "-";
  if (a >= 1e6) return `${s}${(a/1e6).toFixed(1)}М`;
  if (a >= 1e3) return `${s}${(a/1e3).toFixed(1)}К`;
  return `${s}${a.toFixed(0)}`;
}

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

/** Дедупликация по label */
function dedupeByLabel(arr) {
  const seen = new Set();
  return arr.filter(d => {
    if (seen.has(d.label)) return false;
    seen.add(d.label);
    return true;
  });
}

/** Объединение массива серий */
function mergeSeriesData(series) {
  if (!series || series.length === 0) return [];
  const labelMap = {};
  const order = [];
  series.forEach(s => {
    (s.data || []).forEach(d => {
      if (!labelMap[d.label]) {
        labelMap[d.label] = { label: d.label };
        order.push(d.label);
      }
      labelMap[d.label][s.name] = d.value;
    });
  });
  return order.map(l => labelMap[l]);
}

export default function Timeline() {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const cs = useChartSettings();

  // Типы графиков
  const [costType, setCostType] = useState('bar');
  const [countType, setCountType] = useState('bar');
  const [durType, setDurType] = useState('line');

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/timeline', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, monthly_count: rawMonthlyCount, duration, cost } = data;
  const monthly_count = dedupeByLabel(rawMonthlyCount || []);
  const costData = mergeSeriesData(cost);
  const durationData = mergeSeriesData(duration);
  const fsz = cs.fontSizes;
  const fontFamily = cs.font;

  /** Рендер графика стоимости */
  const renderCostChart = () => {
    if (costType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={costData}>
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} tickFormatter={fmtShort} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }}
              formatter={v => [`${fmtShort(v)} ₽`]} />
            <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend }}>{v === 'plan' ? 'План' : 'Факт'}</span>} />
            {cost.find(s => s.name === 'plan') && <Line dataKey="plan" stroke={C.accent} strokeWidth={2} dot={{ r: 4 }} name="plan" />}
            {cost.find(s => s.name === 'fact') && <Line dataKey="fact" stroke={C.warning} strokeWidth={2} dot={{ r: 4 }} name="fact" />}
          </LineChart>
        </ResponsiveContainer>
      );
    }
    if (costType === 'area') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <AreaChart data={costData}>
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} tickFormatter={fmtShort} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }}
              formatter={v => [`${fmtShort(v)} ₽`]} />
            <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend }}>{v === 'plan' ? 'План' : 'Факт'}</span>} />
            {cost.find(s => s.name === 'plan') && <Area type="monotone" dataKey="plan" stroke={C.accent} fill={`${C.accent}20`} strokeWidth={2} name="plan" />}
            {cost.find(s => s.name === 'fact') && <Area type="monotone" dataKey="fact" stroke={C.warning} fill={`${C.warning}20`} strokeWidth={2} name="fact" />}
          </AreaChart>
        </ResponsiveContainer>
      );
    }
    // Bar (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={380}>
        <BarChart data={costData} barCategoryGap="20%">
          <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
          <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} tickFormatter={fmtShort} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }}
            formatter={v => [`${fmtShort(v)} ₽`]} />
          <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend }}>{v === 'plan' ? 'План' : 'Факт'}</span>} />
          {cost.find(s => s.name === 'plan') && (
            <Bar dataKey="plan" fill={C.accent} radius={[4,4,0,0]} name="plan">
              <LabelList dataKey="plan" content={renderBarLabel} />
            </Bar>
          )}
          {cost.find(s => s.name === 'fact') && (
            <Bar dataKey="fact" fill={C.warning} radius={[4,4,0,0]} name="fact">
              <LabelList dataKey="fact" content={renderBarLabel} />
            </Bar>
          )}
        </BarChart>
      </ResponsiveContainer>
    );
  };

  /** Рендер графика количества */
  const renderCountChart = () => {
    if (countType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={monthly_count}>
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }} />
            <Line dataKey="count" stroke={C.accent} strokeWidth={2} dot={{ r: 4 }} name="Заказов" />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    if (countType === 'area') {
      return (
        <ResponsiveContainer width="100%" height={350}>
          <AreaChart data={monthly_count}>
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }} />
            <Area type="monotone" dataKey="count" stroke={C.accent} fill={`${C.accent}20`} strokeWidth={2} name="Заказов" />
          </AreaChart>
        </ResponsiveContainer>
      );
    }
    return (
      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={monthly_count}>
          <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
          <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }} />
          <Bar dataKey="count" fill={C.accent} radius={[4,4,0,0]} name="Заказов">
            <LabelList dataKey="count" content={renderBarLabel} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };

  /** Рендер графика длительности */
  const renderDurationChart = () => {
    if (durType === 'bar') {
      return (
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={durationData} barCategoryGap="20%">
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }} />
            <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend }}>{v === 'plan' ? 'План' : 'Факт'}</span>} />
            {duration.find(s => s.name === 'plan') && <Bar dataKey="plan" fill={C.accent} radius={[4,4,0,0]} name="plan" />}
            {duration.find(s => s.name === 'fact') && <Bar dataKey="fact" fill={C.warning} radius={[4,4,0,0]} name="fact" />}
          </BarChart>
        </ResponsiveContainer>
      );
    }
    if (durType === 'area') {
      return (
        <ResponsiveContainer width="100%" height={350}>
          <AreaChart data={durationData}>
            <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
            <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }} />
            <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend }}>{v === 'plan' ? 'План' : 'Факт'}</span>} />
            {duration.find(s => s.name === 'plan') && <Area type="monotone" dataKey="plan" stroke={C.accent} fill={`${C.accent}20`} strokeWidth={2} name="plan" />}
            {duration.find(s => s.name === 'fact') && <Area type="monotone" dataKey="fact" stroke={C.warning} fill={`${C.warning}20`} strokeWidth={2} name="fact" />}
          </AreaChart>
        </ResponsiveContainer>
      );
    }
    // Line (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={durationData}>
          <XAxis dataKey="label" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} angle={-45} textAnchor="end" height={60} interval={0} allowDuplicatedCategory={false} />
          <YAxis tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontFamily }} />
          <Legend formatter={v => <span style={{ color: C.muted, fontSize: fsz.legend }}>{v === 'plan' ? 'План' : 'Факт'}</span>} />
          {duration.find(s => s.name === 'plan') && <Line dataKey="plan" stroke={C.accent} strokeWidth={2} dot={{ r: 4 }} name="plan" />}
          {duration.find(s => s.name === 'fact') && <Line dataKey="fact" stroke={C.warning} strokeWidth={2} dot={{ r: 4 }} name="fact" />}
        </LineChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div style={{ fontFamily }}>
      <SectionTitle sub="Помесячная аналитика: количество, длительность, стоимость">
        Анализ сроков
      </SectionTitle>

      <KpiRow>
        <KpiCard title="ЗАКАЗОВ С ДАТАМИ" value={kpi.total_with_dates} />
        <KpiCard title="СРЕДН. ДЛИТЕЛЬНОСТЬ" value={`${kpi.avg_duration} дн.`} />
        <KpiCard title="СРЕДН. СТОИМОСТЬ" value={`${fmtShort(kpi.avg_cost)} ₽`} />
      </KpiRow>

      {/* 1. Средняя стоимость */}
      {costData.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>1. Средняя стоимость по месяцам (План и Факт) <ChartSettings chartId="tl-cost" chartTypes={[{value:'bar',label:'Столбцы'},{value:'line',label:'Линия'},{value:'area',label:'Область'}]} currentChartType={costType} onChartTypeChange={setCostType} /></span>}>
          {renderCostChart()}
        </Card>
      )}

      {/* 2. Количество по месяцам */}
      {monthly_count.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>2. Распределение заказов по месяцам <ChartSettings chartId="tl-count" chartTypes={[{value:'bar',label:'Столбцы'},{value:'line',label:'Линия'},{value:'area',label:'Область'}]} currentChartType={countType} onChartTypeChange={setCountType} /></span>}>
          {renderCountChart()}
        </Card>
      )}

      {/* 3. Длительность */}
      {durationData.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>3. Средняя длительность по месяцам (дни) <ChartSettings chartId="tl-dur" chartTypes={[{value:'line',label:'Линия'},{value:'bar',label:'Столбцы'},{value:'area',label:'Область'}]} currentChartType={durType} onChartTypeChange={setDurType} /></span>}>
          {renderDurationChart()}
        </Card>
      )}
    </div>
  );
}
