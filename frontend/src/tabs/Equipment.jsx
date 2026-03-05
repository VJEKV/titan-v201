import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList, LineChart, Line } from 'recharts';
import { C, ABC_COLORS, ABC_ORDER } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet, apiDownload } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import Card from '../components/Card';
import ChartSettings, { useChartSettings } from '../components/ChartSettings';
import DonutWithLegend from '../components/DonutWithLegend';
import StarButton from '../components/StarButton';
import { useStarred } from '../hooks/useStarred';

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

const fmt = v => v ? `${fmtShort(v)} ₽` : '0 ₽';

/** Порядок месяцев для хронологической сортировки */
const MONTH_ORDER = {'Янв':1,'Фев':2,'Мар':3,'Апр':4,'Май':5,'Июн':6,'Июл':7,'Авг':8,'Сен':9,'Окт':10,'Ноя':11,'Дек':12};
function parseMonthLabel(label) {
  if (!label) return { year: 0, month: 0 };
  const parts = label.split(' ');
  const month = MONTH_ORDER[parts[0]] || 0;
  const year = parseInt(parts[1]) || 0;
  return { year, month };
}
function sortMonthLabels(labels) {
  return [...labels].sort((a, b) => {
    const pa = parseMonthLabel(a), pb = parseMonthLabel(b);
    return pa.year !== pb.year ? pa.year - pb.year : pa.month - pb.month;
  });
}

export default function Equipment() {
  const { sessionId, filters, thresholds } = useFilters();
  const { toggleOrder, toggleEO, isOrderStarred, isEOStarred } = useStarred();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [topSort, setTopSort] = useState({ col: 'fact', dir: 'desc' });
  const csAbc = useChartSettings('eq-abc');
  const csClasses = useChartSettings('eq-classes');
  const csFreq = useChartSettings('eq-freq');

  // Типы графиков
  const [classesChartType, setClassesChartType] = useState('hbar');
  const [freqChartType, setFreqChartType] = useState('hbar');

  // TOP-50: развернутые строки (accordion)
  const [expandedEo, setExpandedEo] = useState(null); // код ЕО
  const [expandedOrders, setExpandedOrders] = useState([]);
  const [expandedLoading, setExpandedLoading] = useState(false);

  const toggleExpand = (eoCode) => {
    if (expandedEo === eoCode) {
      setExpandedEo(null);
      setExpandedOrders([]);
      return;
    }
    setExpandedEo(eoCode);
    setExpandedLoading(true);
    apiGet('/api/equipment/orders', { session_id: sessionId, filters, thresholds, eo_code: eoCode })
      .then(res => setExpandedOrders(res.orders || []))
      .catch(() => setExpandedOrders([]))
      .finally(() => setExpandedLoading(false));
  };

  // Аккордион классов: уровень 1 (какой класс раскрыт) + сортировка
  const [expandedClass, setExpandedClass] = useState(null);
  const [classEoList, setClassEoList] = useState([]);
  const [classEoLoading, setClassEoLoading] = useState(false);
  const [classSort, setClassSort] = useState({ col: 'fact', dir: 'desc' });
  // Аккордион классов: уровень 2 (какой ЕО раскрыт) + сортировка
  const [expandedClassEo, setExpandedClassEo] = useState(null);
  const [classEoOrders, setClassEoOrders] = useState([]);
  const [classEoOrdersLoading, setClassEoOrdersLoading] = useState(false);
  const [classEoSort, setClassEoSort] = useState({ col: 'fact', dir: 'desc' });
  // Уровень 3: сортировка заказов
  const [classOrdSort, setClassOrdSort] = useState({ col: 'date_start', dir: 'desc' });

  const handleClassSort = (col) => {
    setClassSort(prev => prev.col === col ? { col, dir: prev.dir === 'desc' ? 'asc' : 'desc' } : { col, dir: col === 'class_name' ? 'asc' : 'desc' });
  };
  const handleClassEoSort = (col) => {
    setClassEoSort(prev => prev.col === col ? { col, dir: prev.dir === 'desc' ? 'asc' : 'desc' } : { col, dir: col === 'name' || col === 'eo' ? 'asc' : 'desc' });
  };
  const handleClassOrdSort = (col) => {
    setClassOrdSort(prev => prev.col === col ? { col, dir: prev.dir === 'desc' ? 'asc' : 'desc' } : { col, dir: col === 'id' || col === 'vid' || col === 'stat' ? 'asc' : 'desc' });
  };

  const toggleClassExpand = (className) => {
    if (expandedClass === className) {
      setExpandedClass(null); setClassEoList([]);
      setExpandedClassEo(null); setClassEoOrders([]);
      return;
    }
    setExpandedClass(className);
    setExpandedClassEo(null); setClassEoOrders([]);
    setClassEoSort({ col: 'fact', dir: 'desc' });
    setClassEoLoading(true);
    apiGet('/api/equipment/by-class', { session_id: sessionId, filters, thresholds, class_name: className })
      .then(res => setClassEoList(res.items || []))
      .catch(() => setClassEoList([]))
      .finally(() => setClassEoLoading(false));
  };

  const toggleClassEoExpand = (eoCode) => {
    if (expandedClassEo === eoCode) {
      setExpandedClassEo(null); setClassEoOrders([]);
      return;
    }
    setExpandedClassEo(eoCode);
    setClassOrdSort({ col: 'date_start', dir: 'desc' });
    setClassEoOrdersLoading(true);
    apiGet('/api/equipment/orders', { session_id: sessionId, filters, thresholds, eo_code: eoCode })
      .then(res => setClassEoOrders(res.orders || []))
      .catch(() => setClassEoOrders([]))
      .finally(() => setClassEoOrdersLoading(false));
  };

  // Частота обслуживания: сортировка + accordion
  const [freqSort, setFreqSort] = useState({ col: 'avg_interval', dir: 'asc' });
  const [freqExpandedEo, setFreqExpandedEo] = useState(null);
  const [freqExpandedOrders, setFreqExpandedOrders] = useState([]);
  const [freqExpandedLoading, setFreqExpandedLoading] = useState(false);

  const handleFreqSort = (col) => {
    if (freqSort.col === col) {
      setFreqSort({ col, dir: freqSort.dir === 'desc' ? 'asc' : 'desc' });
    } else {
      setFreqSort({ col, dir: col === 'equipment_name' || col === 'eo' ? 'asc' : 'desc' });
    }
  };

  const toggleFreqExpand = (eoCode) => {
    if (freqExpandedEo === eoCode) {
      setFreqExpandedEo(null);
      setFreqExpandedOrders([]);
      return;
    }
    setFreqExpandedEo(eoCode);
    setFreqExpandedLoading(true);
    apiGet('/api/equipment/orders', { session_id: sessionId, filters, thresholds, eo_code: eoCode })
      .then(res => setFreqExpandedOrders(res.orders || []))
      .catch(() => setFreqExpandedOrders([]))
      .finally(() => setFreqExpandedLoading(false));
  };

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/equipment', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, abc_data, classes_data, per_eo_data, top50, unplanned_leaders, heatmap, heatmap_eo_stats, frequency, top_date_label, freq_date_label } = data;
  const fs = csAbc.fontSizes;
  const fontFamily = csAbc.font;

  // Сортировка TOP-50
  const handleTopSort = (col) => {
    if (topSort.col === col) {
      setTopSort({ col, dir: topSort.dir === 'desc' ? 'asc' : 'desc' });
    } else {
      setTopSort({ col, dir: 'desc' });
    }
  };

  const sortedTop50 = [...(top50 || [])].sort((a, b) => {
    const dir = topSort.dir === 'desc' ? -1 : 1;
    const av = a[topSort.col], bv = b[topSort.col];
    if (topSort.col === 'abc') return dir * ((ABC_ORDER[av] || 99) - (ABC_ORDER[bv] || 99));
    if (typeof av === 'string') return dir * (av || '').localeCompare(bv || '');
    return dir * ((av || 0) - (bv || 0));
  });

  // Подготовка heatmap: ось X месяцы (хронологический порядок), ось Y ЕО
  const heatmapMonths = sortMonthLabels([...new Set(heatmap.map(h => h.label))]);
  const heatmapEOsRaw = [...new Set(heatmap.map(h => h.eo))];
  // Маппинг eo -> чистое наименование (без кода)
  const eoNameMap = {};
  heatmap.forEach(h => {
    if (!eoNameMap[h.eo]) {
      const parts = h.eo.split(' ');
      const name = parts.length > 1 ? parts.slice(1).join(' ') : h.eo;
      eoNameMap[h.eo] = name;
    }
  });

  const heatmapMap = {};
  let heatMax = 0;
  heatmap.forEach(h => {
    const key = `${h.eo}|${h.label}`;
    heatmapMap[key] = h.value;
    if (h.value > heatMax) heatMax = h.value;
  });

  // Итоговая сумма по ЕО
  const eoTotalMap = {};
  heatmap.forEach(h => {
    eoTotalMap[h.eo] = (eoTotalMap[h.eo] || 0) + (h.value || 0);
  });

  // Сортируем ЕО по количеству заказов (убывание), данные с бэкенда
  const eoStats = heatmap_eo_stats || {};
  const heatmapEOs = [...heatmapEOsRaw].sort((a, b) => {
    const sa = eoStats[a]?.n_orders || 0;
    const sb = eoStats[b]?.n_orders || 0;
    return sb - sa;
  });

  const heatColor = (val) => {
    if (!val || val === 0) return 'transparent';
    const ratio = Math.min(val / Math.max(heatMax, 1), 1);
    if (ratio < 0.2) return `rgba(56,189,248,${0.08 + ratio * 0.3})`;
    if (ratio < 0.4) return `rgba(56,189,248,${0.15 + ratio * 0.5})`;
    if (ratio < 0.6) return `rgba(56,189,248,${0.25 + ratio * 0.5})`;
    if (ratio < 0.8) return `rgba(251,191,36,${0.15 + ratio * 0.35})`;
    return `rgba(244,63,94,${0.2 + ratio * 0.4})`;
  };

  /** Кнопка выгрузки Excel по ЕО */
  const ExcelEoBtn = ({ eo }) => (
    <button onClick={() => apiDownload('/api/export/equipment-excel', { session_id: sessionId, filters, thresholds, eo })}
      style={{ padding: '2px 8px', background: 'none', border: `1px solid ${C.border}`, borderRadius: 4, color: C.accent, cursor: 'pointer', fontSize: 10 }}>
      Excel
    </button>
  );

  // Сортировка для bar chart
  const classesForChart = [...classes_data].sort((a, b) => b.fact - a.fact);

  // Заголовки TOP-50 с сортировкой — Наименование в крайнем левом
  const topDateHint = top_date_label ? ` (${top_date_label})` : '';
  const topHeaders = [
    { key: '#', label: '#', sortable: false },
    { key: 'name', label: 'Наименование', sortable: true },
    { key: 'eo', label: 'Код ЕО', sortable: true },
    { key: 'abc', label: 'ABC', sortable: true },
    { key: 'class_name', label: 'Класс', sortable: true },
    { key: 'n_orders', label: 'Заказов', sortable: true },
    { key: 'plan', label: 'План ₽', sortable: true },
    { key: 'fact', label: 'Факт ₽', sortable: true },
    { key: 'dev', label: 'Откл. ₽', sortable: true },
    { key: 'date_first', label: `Первый${topDateHint}`, sortable: true },
    { key: 'date_last', label: `Последний${topDateHint}`, sortable: true },
    { key: 'downtime_fmt', label: 'Простой', sortable: true },
    { key: '', label: '', sortable: false },
  ];

  /** Цвета ABC для DonutWithLegend — из справочника критичности */
  const abcColors = abc_data.map(d => ABC_COLORS[d.abc] || C.muted);

  /** Рендер графика классов по типу */
  const renderClassesChart = () => {
    const clsMainColor = csClasses.paletteColors[0];
    if (classesChartType === 'vbar') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={classesForChart}>
            <XAxis dataKey="class_name" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} angle={-45} textAnchor="end" height={80} interval={0} />
            <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={fmtShort} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }} formatter={v => [fmt(v)]} />
            <Bar dataKey="fact" fill={clsMainColor} radius={[6,6,0,0]} name="Факт">
              <LabelList dataKey="fact" position="top" fill={C.muted} fontSize={fs.label} formatter={fmtShort} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      );
    }
    if (classesChartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={classesForChart}>
            <XAxis dataKey="class_name" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} angle={-45} textAnchor="end" height={80} interval={0} />
            <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={fmtShort} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }} formatter={v => [fmt(v)]} />
            <Line dataKey="fact" stroke={clsMainColor} strokeWidth={2} dot={{ r: 4, fill: clsMainColor }} name="Факт" />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    // Horizontal bar (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={Math.max(300, classesForChart.length * 40)}>
        <BarChart data={classesForChart} layout="vertical">
          <XAxis type="number" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} tickFormatter={fmtShort} />
          <YAxis type="category" dataKey="class_name" width={140} tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            itemStyle={{ color: C.text }} formatter={v => [fmt(v)]} />
          <Bar dataKey="fact" fill={clsMainColor} radius={[0,6,6,0]} name="Факт">
            <LabelList dataKey="fact" position="right" fill={C.muted} fontSize={fs.label} formatter={fmtShort} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };

  /** Рендер графика частоты по типу (TOP-30 для читаемости) */
  const renderFreqChart = () => {
    const freqMainColor = csFreq.paletteColors[0];
    const freqData = frequency.slice(0, 30).map(f => ({ ...f, eo_label: f.equipment_name ? `${f.eo} ${f.equipment_name}` : f.eo }));
    if (freqChartType === 'vbar') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={freqData}>
            <XAxis dataKey="eo_label" tick={{ fill: C.muted, fontSize: fs.tick - 1, fontFamily }} angle={-45} textAnchor="end" height={100} interval={0}
              tickFormatter={v => v.length > 20 ? v.slice(0,20)+'...' : v} />
            <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }} formatter={v => [`${v} дн.`, 'Средний интервал']} />
            <Bar dataKey="avg_interval" fill={freqMainColor} radius={[6,6,0,0]} name="avg_interval">
              <LabelList dataKey="avg_interval" position="top" fill={C.muted} fontSize={fs.label - 1} formatter={v => `${v} дн.`} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      );
    }
    if (freqChartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={freqData}>
            <XAxis dataKey="eo_label" tick={{ fill: C.muted, fontSize: fs.tick - 1, fontFamily }} angle={-45} textAnchor="end" height={100} interval={0}
              tickFormatter={v => v.length > 20 ? v.slice(0,20)+'...' : v} />
            <YAxis tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} />
            <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
              itemStyle={{ color: C.text }} formatter={v => [`${v} дн.`, 'Средний интервал']} />
            <Line dataKey="avg_interval" stroke={freqMainColor} strokeWidth={2} dot={{ r: 4, fill: freqMainColor }} name="avg_interval" />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    // Horizontal bar (по умолчанию)
    return (
      <ResponsiveContainer width="100%" height={Math.max(350, frequency.length * 28)}>
        <BarChart data={freqData} layout="vertical">
          <XAxis type="number" tick={{ fill: C.muted, fontSize: fs.tick, fontFamily }} label={{ value: 'дней', position: 'insideBottomRight', fill: C.dim, fontSize: fs.label - 2 }} />
          <YAxis type="category" dataKey="eo_label" width={200} tick={{ fill: C.muted, fontSize: fs.tick - 1, fontFamily }}
            tickFormatter={v => v.length > 28 ? v.slice(0,28)+'...' : v} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            itemStyle={{ color: C.text }}
            formatter={(v, name) => [name === 'avg_interval' ? `${v} дн.` : v, 'Средний интервал']} />
          <Bar dataKey="avg_interval" fill={freqMainColor} radius={[0,6,6,0]} name="avg_interval">
            <LabelList dataKey="avg_interval" position="right" fill={C.muted} fontSize={fs.label - 1} formatter={v => `${v} дн.`} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div style={{ fontFamily }}>
      <SectionTitle sub="Классификация, метрики по классам, TOP-50, heatmap, частота обслуживания">
        Аналитика по оборудованию
      </SectionTitle>

      {/* KPI */}
      <KpiRow>
        <KpiCard title="ВСЕГО ЕО" value={fmtNum(kpi.total_eo)} />
        <KpiCard title="ОСОБО КРИТ." value={fmtNum(kpi.abc_osob)} color="#9f1239" />
        <KpiCard title="ВЫСОКО КРИТ." value={fmtNum(kpi.abc_vysok)} color={C.danger} />
        <KpiCard title="НИЗКОЙ КРИТ." value={fmtNum(kpi.abc_low)} color={C.warning} />
        <KpiCard title="НЕ КРИТИЧНО" value={fmtNum(kpi.abc_none)} color={C.accent} />
        <KpiCard title="БЕЗ ЕО (ЗАКАЗОВ)" value={fmtNum(kpi.no_eo_orders)} color={C.dim} />
      </KpiRow>

{/* ABC-распределение */}
      {abc_data && abc_data.length > 0 && (
        <Card title="1. ABC-критичность оборудования">
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
            <ChartSettings chartId="eq-abc" />
          </div>
          <DonutWithLegend
            data={abc_data.map(d => ({ name: d.abc, value: d.sum, count: d.count, pct: d.pct }))}
            colors={abcColors}
            chartId="eq-abc"
            fontSize={fs.pie || 12}
            fontFamily={fontFamily}
          />
        </Card>
      )}

      {/* 2. Таблица классов оборудования */}
      {classes_data.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>2. Классы оборудования — метрики <ChartSettings chartId="eq-classes" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'},{value:'line',label:'Линия'}]} currentChartType={classesChartType} onChartTypeChange={setClassesChartType} /></span>}>
          <div>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                    {[{key:'class_name',label:'Класс'},{key:'n_eo',label:'ЕО'},{key:'n_orders',label:'Заказов'},{key:'plan',label:'План ₽'},{key:'fact',label:'Факт ₽'},{key:'dev',label:'Откл. ₽'},{key:'downtime_fmt',label:'Простой'},{key:'',label:''}].map(h => (
                      <th key={h.key||h.label} onClick={h.key ? () => handleClassSort(h.key) : undefined}
                        style={{ color: classSort.col === h.key ? C.accent : C.muted, fontSize: 11, padding: '8px 10px', whiteSpace: 'nowrap', cursor: h.key ? 'pointer' : 'default', userSelect: 'none' }}>
                        {h.label} {classSort.col === h.key ? (classSort.dir === 'desc' ? '▼' : '▲') : ''}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...classes_data].sort((a, b) => {
                    const dir = classSort.dir === 'desc' ? -1 : 1;
                    const av = a[classSort.col], bv = b[classSort.col];
                    if (typeof av === 'string') return dir * av.localeCompare(bv);
                    return dir * ((av || 0) - (bv || 0));
                  }).map((r, i) => {
                    const isClassExpanded = expandedClass === r.class_name;
                    return (
                      <React.Fragment key={i}>
                        <tr style={{ borderBottom: `1px solid ${C.border}33`, cursor: 'pointer' }} onClick={() => toggleClassExpand(r.class_name)}>
                          <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px', whiteSpace: 'nowrap' }}>
                            {isClassExpanded ? '▼ ' : '▶ '}{r.class_name}
                          </td>
                          <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{fmtNum(r.n_eo)}</td>
                          <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{fmtNum(r.n_orders)}</td>
                          <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.plan)} ₽</td>
                          <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.fact)} ₽</td>
                          <td style={{ color: r.dev > 0 ? C.danger : r.dev < 0 ? C.success : C.muted, fontSize: 12, textAlign: 'right', padding: '6px 10px', fontWeight: 600 }}>
                            {r.dev > 0 ? '+' : ''}{fmtShort(r.dev)} ₽
                          </td>
                          <td style={{ color: r.downtime_fmt && r.downtime_fmt !== '0' ? C.accent : C.dim, fontSize: 12, padding: '6px 10px', whiteSpace: 'nowrap' }}>
                            {r.downtime_fmt && r.downtime_fmt !== '0' ? r.downtime_fmt : '—'}
                          </td>
                          <td style={{ padding: '6px 10px' }} onClick={e => e.stopPropagation()}>
                            <button onClick={() => apiDownload('/api/export/equipment-class-excel', { session_id: sessionId, filters, thresholds, class_name: r.class_name })}
                              style={{ padding: '2px 8px', background: 'none', border: `1px solid ${C.border}`, borderRadius: 4, color: C.accent, cursor: 'pointer', fontSize: 10 }}>
                              Excel
                            </button>
                          </td>
                        </tr>
                        {isClassExpanded && (
                          <tr>
                            <td colSpan={8} style={{ padding: 0 }}>
                              <div style={{
                                background: 'linear-gradient(145deg, #1e293b 0%, #1a2332 100%)',
                                padding: '12px 16px', borderLeft: `3px solid ${C.accent}`,
                                margin: '0 8px 8px 8px', borderRadius: '0 0 8px 8px',
                              }}>
                                {classEoLoading ? (
                                  <p style={{ color: C.muted, fontSize: 12 }}>Загрузка оборудования...</p>
                                ) : classEoList.length === 0 ? (
                                  <p style={{ color: C.muted, fontSize: 12 }}>Нет оборудования</p>
                                ) : (
                                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead>
                                      <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                                        {[{key:'eo',label:'Код ЕО'},{key:'name',label:'Название'},{key:'abc',label:'ABC'},{key:'n_orders',label:'Заказов'},{key:'plan',label:'План ₽'},{key:'fact',label:'Факт ₽'},{key:'dev',label:'Откл. ₽'},{key:'',label:''}].map(h => (
                                          <th key={h.key||h.label} onClick={h.key ? (e) => { e.stopPropagation(); handleClassEoSort(h.key); } : undefined}
                                            style={{ color: classEoSort.col === h.key ? C.accent : C.dim, fontSize: 10, padding: '4px 8px', textAlign: 'left', fontWeight: 600, cursor: h.key ? 'pointer' : 'default', userSelect: 'none' }}>
                                            {h.label} {classEoSort.col === h.key ? (classEoSort.dir === 'desc' ? '▼' : '▲') : ''}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {[...classEoList].sort((a, b) => {
                                        const dir = classEoSort.dir === 'desc' ? -1 : 1;
                                        const av = a[classEoSort.col], bv = b[classEoSort.col];
                                        if (classEoSort.col === 'abc') return dir * ((ABC_ORDER[av] || 99) - (ABC_ORDER[bv] || 99));
                                        if (typeof av === 'string') return dir * (av || '').localeCompare(bv || '');
                                        return dir * ((av || 0) - (bv || 0));
                                      }).map((eo, j) => {
                                        const isEoExpanded = expandedClassEo === eo.eo;
                                        return (
                                          <React.Fragment key={j}>
                                            <tr style={{ borderBottom: `1px solid ${C.border}22`, cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); toggleClassEoExpand(eo.eo); }}>
                                              <td style={{ color: C.accent, fontSize: 11, padding: '4px 8px', fontWeight: 600 }}>{eo.eo}</td>
                                              <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                                title={eo.name}>
                                                {isEoExpanded ? '▼ ' : '▶ '}
                                                <StarButton active={isEOStarred(eo.name)} onClick={() => toggleEO(eo.name)} size={10} />{' '}{eo.name}
                                              </td>
                                              <td style={{ color: ABC_COLORS[eo.abc] || C.muted, fontSize: 11, fontWeight: 600, padding: '4px 8px' }}>{eo.abc || '—'}</td>
                                              <td style={{ color: C.text, fontSize: 11, textAlign: 'center', padding: '4px 8px' }}>{eo.n_orders}</td>
                                              <td style={{ color: C.text, fontSize: 11, textAlign: 'right', padding: '4px 8px' }}>{fmtShort(eo.plan)} ₽</td>
                                              <td style={{ color: C.text, fontSize: 11, textAlign: 'right', padding: '4px 8px' }}>{fmtShort(eo.fact)} ₽</td>
                                              <td style={{ color: eo.dev > 0 ? C.danger : eo.dev < 0 ? C.success : C.muted, fontSize: 11, textAlign: 'right', padding: '4px 8px', fontWeight: 600 }}>
                                                {eo.dev > 0 ? '+' : ''}{fmtShort(eo.dev)} ₽
                                              </td>
                                              <td style={{ padding: '4px 8px' }} onClick={e => e.stopPropagation()}>
                                                <ExcelEoBtn eo={eo.eo} />
                                              </td>
                                            </tr>
                                            {isEoExpanded && (
                                              <tr>
                                                <td colSpan={8} style={{ padding: 0 }}>
                                                  <div style={{
                                                    background: 'linear-gradient(145deg, #1a2332 0%, #162030 100%)',
                                                    padding: '10px 14px', borderLeft: `3px solid ${C.cyan}`,
                                                    margin: '0 6px 6px 20px', borderRadius: '0 0 8px 8px',
                                                  }}>
                                                    {classEoOrdersLoading ? (
                                                      <p style={{ color: C.muted, fontSize: 11 }}>Загрузка заказов...</p>
                                                    ) : classEoOrders.length === 0 ? (
                                                      <p style={{ color: C.muted, fontSize: 11 }}>Нет заказов</p>
                                                    ) : (
                                                      <>
                                                      <div style={{ fontSize: 10, color: C.dim, marginBottom: 6 }}>
                                                        <span style={{ color: C.success }}>зелёный</span> — факт, <span style={{ color: C.accent }}>синий ○</span> — сообщ., <span style={{ color: C.warning }}>жёлтый •</span> — план, <span style={{ color: C.danger }}>красный</span> — нет
                                                      </div>
                                                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                                        <thead>
                                                          <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                                                            {[{key:'id',label:'Заказ'},{key:'date_start',label:'Дата нач.'},{key:'date_end',label:'Дата кон.'},{key:'vid',label:'Вид работ'},{key:'rm',label:'РМ'},{key:'stat',label:'Статус'},{key:'plan',label:'План ₽'},{key:'fact',label:'Факт ₽'},{key:'dev',label:'Откл. ₽'}].map(h => (
                                                              <th key={h.key} onClick={(e) => { e.stopPropagation(); handleClassOrdSort(h.key); }}
                                                                style={{ color: classOrdSort.col === h.key ? C.accent : C.dim, fontSize: 10, padding: '4px 6px', textAlign: 'left', fontWeight: 600, cursor: 'pointer', userSelect: 'none' }}>
                                                                {h.label} {classOrdSort.col === h.key ? (classOrdSort.dir === 'desc' ? '▼' : '▲') : ''}
                                                              </th>
                                                            ))}
                                                          </tr>
                                                        </thead>
                                                        <tbody>
                                                          {[...classEoOrders].sort((a, b) => {
                                                            const dir = classOrdSort.dir === 'desc' ? -1 : 1;
                                                            const col = classOrdSort.col;
                                                            if (col === 'date_start' || col === 'date_end') {
                                                              const pa = (a[col]||'').split('.'), pb = (b[col]||'').split('.');
                                                              const da = pa.length===3 ? `${pa[2]}${pa[1]}${pa[0]}` : a[col]||'';
                                                              const db = pb.length===3 ? `${pb[2]}${pb[1]}${pb[0]}` : b[col]||'';
                                                              return dir * da.localeCompare(db);
                                                            }
                                                            const av = a[col], bv = b[col];
                                                            if (typeof av === 'string') return dir * (av || '').localeCompare(bv || '');
                                                            return dir * ((av || 0) - (bv || 0));
                                                          }).map((ord, k) => {
                                                            const dClr = ord.date_source === 'FACT' ? C.success : ord.date_source === 'NOTIFY' ? C.accent : ord.date_source === 'PLAN' ? C.warning : C.danger;
                                                            const pm = ord.date_source === 'PLAN' ? ' \u2022' : ord.date_source === 'NOTIFY' ? ' \u25cb' : '';
                                                            const ordDev = (ord.dev != null) ? ord.dev : (ord.fact || 0) - (ord.plan || 0);
                                                            return (
                                                            <tr key={k} style={{ borderBottom: `1px solid ${C.border}22` }}>
                                                              <td style={{ color: C.accent, fontSize: 10, padding: '3px 6px', fontWeight: 600 }}>
                                                                <StarButton active={isOrderStarred(ord.id)} onClick={() => toggleOrder(ord.id)} size={10} />{' '}{ord.id}
                                                              </td>
                                                              <td style={{ color: dClr, fontSize: 10, padding: '3px 6px', whiteSpace: 'nowrap' }}>{ord.date_start ? ord.date_start + pm : '—'}</td>
                                                              <td style={{ color: dClr, fontSize: 10, padding: '3px 6px', whiteSpace: 'nowrap' }}>{ord.date_end ? ord.date_end + pm : '—'}</td>
                                                              <td style={{ color: C.text, fontSize: 10, padding: '3px 6px' }}>{ord.vid}</td>
                                                              <td style={{ color: C.muted, fontSize: 10, padding: '3px 6px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={ord.rm}>{ord.rm || '—'}</td>
                                                              <td style={{ color: C.muted, fontSize: 10, padding: '3px 6px' }}>{ord.stat}</td>
                                                              <td style={{ color: C.text, fontSize: 10, padding: '3px 6px', textAlign: 'right' }}>{fmtShort(ord.plan)}</td>
                                                              <td style={{ color: C.text, fontSize: 10, padding: '3px 6px', textAlign: 'right' }}>{fmtShort(ord.fact)}</td>
                                                              <td style={{ color: ordDev > 0 ? C.danger : ordDev < 0 ? C.success : C.muted, fontSize: 10, padding: '3px 6px', textAlign: 'right', fontWeight: 600 }}>
                                                                {ordDev > 0 ? '+' : ''}{fmtShort(ordDev)} ₽
                                                              </td>
                                                            </tr>
                                                            );
                                                          })}
                                                        </tbody>
                                                      </table>
                                                      </>
                                                    )}
                                                  </div>
                                                </td>
                                              </tr>
                                            )}
                                          </React.Fragment>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}

      {/* 3. Метрики на единицу ЕО */}
      {per_eo_data.length > 0 && (
        <Card title="3. Метрики на единицу оборудования">
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                  {['Класс', 'Ср. заказов/ЕО', 'Ср. план/ЕО ₽', 'Ср. факт/ЕО ₽'].map(h => (
                    <th key={h} style={{ color: C.muted, fontSize: 11, padding: '8px 10px', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {per_eo_data.map((r, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                    <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px' }}>{r.class_name}</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{r.avg_orders}</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.avg_plan)} ₽</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.avg_cost)} ₽</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* 4. TOP-50 ЕО по затратам — с сортировкой */}
      {sortedTop50.length > 0 && (
        <Card title="4. TOP-50 единиц оборудования по затратам">
          <div style={{ overflowX: 'auto', borderRadius: 8, border: `1px solid ${C.border}` }}>
            <table>
              <thead>
                <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                  {topHeaders.map(h => (
                    <th key={h.key || h.label} onClick={h.sortable ? () => handleTopSort(h.key) : undefined}
                      style={{
                        color: topSort.col === h.key ? C.accent : C.muted,
                        fontSize: 11, padding: '8px 10px', whiteSpace: 'nowrap',
                        cursor: h.sortable ? 'pointer' : 'default',
                        userSelect: 'none',
                      }}>
                      {h.label} {topSort.col === h.key ? (topSort.dir === 'desc' ? '▼' : '▲') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedTop50.map((r, i) => {
                  const isExpanded = expandedEo === r.eo;
                  return (
                    <React.Fragment key={i}>
                      <tr style={{ borderBottom: `1px solid ${C.border}33`, cursor: 'pointer' }}>
                        <td style={{ color: C.dim, fontSize: 12, padding: '6px 10px' }}>{i + 1}</td>
                        <td onClick={() => toggleExpand(r.eo)}
                          style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'pointer' }}
                          title={`${r.name} — нажмите для детализации`}>
                          {isExpanded ? '▼ ' : '▶ '}
                          <StarButton active={isEOStarred(r.name)} onClick={() => toggleEO(r.name)} size={12} />{' '}{r.name}
                        </td>
                        <td style={{ color: C.muted, fontSize: 12, padding: '6px 10px' }}>{r.eo}</td>
                        <td style={{ color: ABC_COLORS[r.abc] || C.muted, fontSize: 12, fontWeight: 600, padding: '6px 10px', textAlign: 'center' }}>{r.abc || '—'}</td>
                        <td style={{ color: C.muted, fontSize: 12, padding: '6px 10px' }}>{r.class_name}</td>
                        <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{r.n_orders}</td>
                        <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.plan)} ₽</td>
                        <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.fact)} ₽</td>
                        <td style={{ color: r.dev > 0 ? C.danger : r.dev < 0 ? C.success : C.muted, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>
                          {r.dev > 0 ? '+' : ''}{fmtShort(r.dev)} ₽
                        </td>
                        <td style={{ color: C.muted, fontSize: 11, padding: '6px 10px', whiteSpace: 'nowrap' }}>{r.date_first || '—'}</td>
                        <td style={{ color: C.muted, fontSize: 11, padding: '6px 10px', whiteSpace: 'nowrap' }}>{r.date_last || '—'}</td>
                        <td style={{ color: r.downtime_fmt && r.downtime_fmt !== '0' ? C.accent : C.dim, fontSize: 11, padding: '6px 10px', whiteSpace: 'nowrap' }}>{r.downtime_fmt && r.downtime_fmt !== '0' ? r.downtime_fmt : '—'}</td>
                        <td style={{ padding: '6px 10px' }}><ExcelEoBtn eo={r.eo} /></td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={topHeaders.length} style={{ padding: 0 }}>
                            <div style={{
                              background: 'linear-gradient(145deg, #1e293b 0%, #1a2332 100%)',
                              padding: '12px 16px', borderLeft: `3px solid ${C.accent}`,
                              margin: '0 8px 8px 8px', borderRadius: '0 0 8px 8px',
                            }}>
                              {expandedLoading ? (
                                <p style={{ color: C.muted, fontSize: 12 }}>Загрузка заказов...</p>
                              ) : expandedOrders.length === 0 ? (
                                <p style={{ color: C.muted, fontSize: 12 }}>Нет заказов</p>
                              ) : (
                                <>
                                <div style={{ fontSize: 10, color: C.dim, marginBottom: 6 }}>
                                  <span style={{ color: C.success }}>зелёный</span> — факт, <span style={{ color: C.accent }}>синий ○</span> — сообщ., <span style={{ color: C.warning }}>жёлтый •</span> — план, <span style={{ color: C.danger }}>красный</span> — нет
                                </div>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                  <thead>
                                    <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                                      {['Заказ', 'Дата нач.', 'Дата кон.', 'Вид работ', 'РМ', 'Статус', 'Текст работ', 'План ₽', 'Факт ₽', 'Откл. ₽'].map(h => (
                                        <th key={h} style={{ color: C.dim, fontSize: 10, padding: '4px 8px', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {expandedOrders.map((ord, j) => {
                                      const dClr = ord.date_source === 'FACT' ? C.success : ord.date_source === 'NOTIFY' ? C.accent : ord.date_source === 'PLAN' ? C.warning : C.danger;
                                      const pm = ord.date_source === 'PLAN' ? ' \u2022' : ord.date_source === 'NOTIFY' ? ' \u25cb' : '';
                                      const oDev = (ord.dev != null) ? ord.dev : (ord.fact || 0) - (ord.plan || 0);
                                      return (
                                      <tr key={j} style={{ borderBottom: `1px solid ${C.border}22` }}>
                                        <td style={{ color: C.accent, fontSize: 11, padding: '4px 8px', fontWeight: 600 }}>
                                          <StarButton active={isOrderStarred(ord.id)} onClick={() => toggleOrder(ord.id)} size={11} />{' '}{ord.id}
                                        </td>
                                        <td style={{ color: dClr, fontSize: 11, padding: '4px 8px', whiteSpace: 'nowrap' }}>{ord.date_start ? ord.date_start + pm : '—'}</td>
                                        <td style={{ color: dClr, fontSize: 11, padding: '4px 8px', whiteSpace: 'nowrap' }}>{ord.date_end ? ord.date_end + pm : '—'}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px' }}>{ord.vid}</td>
                                        <td style={{ color: C.muted, fontSize: 11, padding: '4px 8px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={ord.rm}>{ord.rm || '—'}</td>
                                        <td style={{ color: C.muted, fontSize: 11, padding: '4px 8px' }}>{ord.stat}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                          title={ord.text}>{ord.text}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', textAlign: 'right' }}>{fmtShort(ord.plan)}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', textAlign: 'right' }}>{fmtShort(ord.fact)}</td>
                                        <td style={{ color: oDev > 0 ? C.danger : oDev < 0 ? C.success : C.muted, fontSize: 11, padding: '4px 8px', textAlign: 'right', fontWeight: 600 }}>
                                          {oDev > 0 ? '+' : ''}{fmtShort(oDev)} ₽
                                        </td>
                                      </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* 5. Лидеры по внеплановым среди A и B */}
      {unplanned_leaders.length > 0 && (
        <Card title="5. Лидеры по корректирующим/внеплановым работам (ABC: A, B)" borderColor={C.danger}>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                  {['Класс', 'Внеплановых заказов', 'Факт ₽', ''].map(h => (
                    <th key={h || 'excel'} style={{ color: C.muted, fontSize: 11, padding: '8px 10px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {unplanned_leaders.map((r, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                    <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px' }}>{r.class_name}</td>
                    <td style={{ color: C.danger, fontSize: 12, textAlign: 'center', fontWeight: 600, padding: '6px 10px' }}>{r.n_orders}</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.fact)} ₽</td>
                    <td style={{ padding: '6px 10px' }}>
                      <button onClick={() => apiDownload('/api/export/equipment-class-excel', { session_id: sessionId, filters, thresholds, class_name: r.class_name, unplanned: true })}
                        style={{ padding: '2px 8px', background: 'none', border: `1px solid ${C.border}`, borderRadius: 4, color: C.accent, cursor: 'pointer', fontSize: 10 }}>
                        Excel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* 6. Heatmap: месяцы × TOP-100 ЕО — без кода ЕО, с итогом */}
      {heatmapEOs.length > 0 && heatmapMonths.length > 0 && (
        <Card title={`6. Heatmap затрат: месяцы × TOP-${heatmapEOs.length} ЕО`}>
          <div style={{ overflowX: 'auto', maxHeight: 900, overflowY: 'auto', borderRadius: 8, border: `1px solid ${C.border}` }}>
            <table>
              <thead style={{ position: 'sticky', top: 0, zIndex: 2 }}>
                <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                  <th style={{ color: C.muted, fontSize: 10, padding: '6px 8px', position: 'sticky', left: 0, background: C.bg, zIndex: 3, minWidth: 340 }}>Наименование ЕО | Заказов | Сумма ₽</th>
                  {heatmapMonths.map(m => (
                    <th key={m} style={{ color: C.muted, fontSize: 10, padding: '6px 6px', whiteSpace: 'nowrap', textAlign: 'center' }}>{m}</th>
                  ))}
                  <th style={{ color: C.accent, fontSize: 10, padding: '6px 8px', whiteSpace: 'nowrap', textAlign: 'right', fontWeight: 700 }}>Итого ₽</th>
                </tr>
              </thead>
              <tbody>
                {heatmapEOs.map((eo, i) => {
                  const name = eoNameMap[eo] || eo;
                  const total = eoTotalMap[eo] || 0;
                  const stats = eoStats[eo] || {};
                  const nOrders = stats.n_orders || 0;
                  const totalFact = stats.total_fact || 0;
                  return (
                    <tr key={i} style={{ borderBottom: `1px solid ${C.border}22` }}>
                      <td style={{ color: C.text, fontSize: 10, padding: '4px 8px', whiteSpace: 'nowrap', position: 'sticky', left: 0, background: C.surface, zIndex: 1, maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis' }}
                        title={eo}>
                        <StarButton active={isEOStarred(name)} onClick={() => toggleEO(name)} size={10} />{' '}
                        <span>{name.length > 22 ? name.slice(0,22)+'...' : name}</span>
                        <span style={{ color: C.muted, marginLeft: 6 }}>|</span>
                        <span style={{ color: C.accent, marginLeft: 4 }}>{nOrders} зак.</span>
                        <span style={{ color: C.muted, marginLeft: 4 }}>|</span>
                        <span style={{ color: C.warning, marginLeft: 4 }}>{fmtShort(totalFact)} ₽</span>
                      </td>
                      {heatmapMonths.map(m => {
                        const val = heatmapMap[`${eo}|${m}`] || 0;
                        return (
                          <td key={m} style={{ background: heatColor(val), color: val > 0 ? C.text : C.dim, fontSize: 11, textAlign: 'center', padding: '4px 6px' }}>
                            {val > 0 ? fmtShort(val) : ''}
                          </td>
                        );
                      })}
                      <td style={{ color: C.accent, fontSize: 10, textAlign: 'right', padding: '4px 8px', fontWeight: 600 }}>
                        {fmtShort(total)} ₽
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div style={{ fontSize: 11, color: C.dim, marginTop: 6 }}>
            Показано {heatmapEOs.length} ЕО. Прокрутите таблицу для просмотра всех.
          </div>
        </Card>
      )}

      {/* 7. Частота обслуживания */}
      {frequency.length > 0 && (() => {
        // Сортировка частоты
        const freqDateHint = freq_date_label ? ` (${freq_date_label})` : '';
        const freqHeaders = [
          { key: 'eo', label: 'Код ЕО' },
          { key: 'equipment_name', label: 'Название ЕО' },
          { key: 'abc', label: 'ABC' },
          { key: 'n_orders', label: 'Заказов' },
          { key: 'total_plan', label: 'План ₽' },
          { key: 'total_fact', label: 'Факт ₽' },
          { key: 'avg_interval', label: 'Ср. интервал (дни)' },
          { key: 'min_interval', label: 'Мин инт.' },
          { key: 'max_interval', label: 'Макс инт.' },
          { key: 'date_first', label: `Первый${freqDateHint}` },
          { key: 'date_last', label: `Последний${freqDateHint}` },
        ];
        const sortedFreq = [...frequency].sort((a, b) => {
          const dir = freqSort.dir === 'desc' ? -1 : 1;
          const av = a[freqSort.col], bv = b[freqSort.col];
          if (freqSort.col === 'abc') return dir * ((ABC_ORDER[av] || 99) - (ABC_ORDER[bv] || 99));
          if (typeof av === 'string') return dir * (av || '').localeCompare(bv || '');
          return dir * ((av || 0) - (bv || 0));
        });
        return (
        <Card title="7. Частота обслуживания — средний интервал между заказами (дни)">
          <div style={{ fontSize: 12, color: C.muted, marginBottom: 8 }}>
            TOP-{frequency.length} ЕО с 2+ заказами. Нажмите на заголовок столбца для сортировки, на название ЕО — для детализации заказов.
          </div>
          {/* Таблица частоты обслуживания — 30 видимых, остальные в прокрутку */}
          <div style={{ overflowX: 'auto', maxHeight: 30 * 36 + 42, overflowY: 'auto', marginBottom: 16, borderRadius: 8, border: `1px solid ${C.border}` }}>
            <table>
              <thead style={{ position: 'sticky', top: 0, zIndex: 2 }}>
                <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                  <th style={{ color: C.dim, fontSize: 11, padding: '8px 6px', width: 30 }}>#</th>
                  {freqHeaders.map(h => (
                    <th key={h.key}
                      onClick={() => handleFreqSort(h.key)}
                      style={{
                        color: freqSort.col === h.key ? C.accent : C.muted,
                        fontSize: 11, padding: '8px 10px', whiteSpace: 'nowrap',
                        cursor: 'pointer', userSelect: 'none',
                      }}>
                      {h.label} {freqSort.col === h.key ? (freqSort.dir === 'desc' ? '▼' : '▲') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedFreq.map((f, i) => {
                  const isFreqExpanded = freqExpandedEo === f.eo;
                  return (
                    <React.Fragment key={i}>
                      <tr style={{ borderBottom: `1px solid ${C.border}33` }}>
                        <td style={{ color: C.dim, fontSize: 11, padding: '6px 6px', textAlign: 'center' }}>{i + 1}</td>
                        <td style={{ color: C.accent, fontSize: 12, fontWeight: 600, padding: '6px 10px' }}>{f.eo}</td>
                        <td onClick={() => toggleFreqExpand(f.eo)}
                          style={{ color: C.text, fontSize: 12, padding: '6px 10px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'pointer' }}
                          title={`${f.equipment_name || '—'} — нажмите для детализации`}>
                          {isFreqExpanded ? '▼ ' : '▶ '}
                          <StarButton active={isEOStarred(f.equipment_name)} onClick={() => toggleEO(f.equipment_name)} size={11} />{' '}{f.equipment_name || '—'}
                        </td>
                        <td style={{ color: ABC_COLORS[f.abc] || C.muted, fontSize: 12, fontWeight: 600, padding: '6px 10px', textAlign: 'center' }}>{f.abc || '—'}</td>
                        <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{f.n_orders}</td>
                        <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(f.total_plan)} ₽</td>
                        <td style={{ color: C.orange, fontSize: 12, textAlign: 'right', padding: '6px 10px', fontWeight: 600 }}>{fmtShort(f.total_fact)} ₽</td>
                        <td style={{ color: C.warning, fontSize: 12, textAlign: 'center', padding: '6px 10px', fontWeight: 600 }}>{f.avg_interval} дн.</td>
                        <td style={{ color: C.success, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{f.min_interval ?? '—'} дн.</td>
                        <td style={{ color: C.danger, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{f.max_interval ?? '—'} дн.</td>
                        <td style={{ color: C.muted, fontSize: 11, padding: '6px 10px', whiteSpace: 'nowrap' }}>{f.date_first || '—'}</td>
                        <td style={{ color: C.muted, fontSize: 11, padding: '6px 10px', whiteSpace: 'nowrap' }}>{f.date_last || '—'}</td>
                      </tr>
                      {isFreqExpanded && (
                        <tr>
                          <td colSpan={freqHeaders.length + 1} style={{ padding: 0 }}>
                            <div style={{
                              background: 'linear-gradient(145deg, #1e293b 0%, #1a2332 100%)',
                              padding: '12px 16px', borderLeft: `3px solid ${C.cyan}`,
                              margin: '0 8px 8px 8px', borderRadius: '0 0 8px 8px',
                            }}>
                              {freqExpandedLoading ? (
                                <p style={{ color: C.muted, fontSize: 12 }}>Загрузка заказов...</p>
                              ) : freqExpandedOrders.length === 0 ? (
                                <p style={{ color: C.muted, fontSize: 12 }}>Нет заказов</p>
                              ) : (
                                <>
                                <div style={{ fontSize: 10, color: C.dim, marginBottom: 6 }}>
                                  <span style={{ color: C.success }}>зелёный</span> — факт, <span style={{ color: C.accent }}>синий ○</span> — сообщ., <span style={{ color: C.warning }}>жёлтый •</span> — план, <span style={{ color: C.danger }}>красный</span> — нет
                                </div>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                  <thead>
                                    <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                                      {['Заказ', 'Дата нач.', 'Дата кон.', 'Вид работ', 'РМ', 'Статус', 'Текст работ', 'План ₽', 'Факт ₽', 'Откл. ₽'].map(h => (
                                        <th key={h} style={{ color: C.dim, fontSize: 10, padding: '4px 8px', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {freqExpandedOrders.map((ord, j) => {
                                      const dClr = ord.date_source === 'FACT' ? C.success : ord.date_source === 'NOTIFY' ? C.accent : ord.date_source === 'PLAN' ? C.warning : C.danger;
                                      const pm = ord.date_source === 'PLAN' ? ' \u2022' : ord.date_source === 'NOTIFY' ? ' \u25cb' : '';
                                      const fDev = (ord.dev != null) ? ord.dev : (ord.fact || 0) - (ord.plan || 0);
                                      return (
                                      <tr key={j} style={{ borderBottom: `1px solid ${C.border}22` }}>
                                        <td style={{ color: C.accent, fontSize: 11, padding: '4px 8px', fontWeight: 600 }}>
                                          <StarButton active={isOrderStarred(ord.id)} onClick={() => toggleOrder(ord.id)} size={11} />{' '}{ord.id}
                                        </td>
                                        <td style={{ color: dClr, fontSize: 11, padding: '4px 8px', whiteSpace: 'nowrap' }}>{ord.date_start ? ord.date_start + pm : '—'}</td>
                                        <td style={{ color: dClr, fontSize: 11, padding: '4px 8px', whiteSpace: 'nowrap' }}>{ord.date_end ? ord.date_end + pm : '—'}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px' }}>{ord.vid}</td>
                                        <td style={{ color: C.muted, fontSize: 11, padding: '4px 8px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={ord.rm}>{ord.rm || '—'}</td>
                                        <td style={{ color: C.muted, fontSize: 11, padding: '4px 8px' }}>{ord.stat}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                          title={ord.text}>{ord.text}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', textAlign: 'right' }}>{fmtShort(ord.plan)}</td>
                                        <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', textAlign: 'right' }}>{fmtShort(ord.fact)}</td>
                                        <td style={{ color: fDev > 0 ? C.danger : fDev < 0 ? C.success : C.muted, fontSize: 11, padding: '4px 8px', textAlign: 'right', fontWeight: 600 }}>
                                          {fDev > 0 ? '+' : ''}{fmtShort(fDev)} ₽
                                        </td>
                                      </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
        );
      })()}
    </div>
  );
}
