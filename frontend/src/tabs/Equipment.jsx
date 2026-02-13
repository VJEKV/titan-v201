import { useState, useEffect } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList, LineChart, Line, AreaChart, Area } from 'recharts';
import { C, ABC_COLORS, CHART_COLORS } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet, apiDownload } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import Card from '../components/Card';
import ChartSettings, { useChartSettings, getColorsForChart } from '../components/ChartSettings';

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

const RADIAN = Math.PI / 180;

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
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [topSort, setTopSort] = useState({ col: 'fact', dir: 'desc' });
  const cs = useChartSettings();

  // Типы графиков
  const [abcChartType, setAbcChartType] = useState('donut');
  const [classesChartType, setClassesChartType] = useState('hbar');
  const [freqChartType, setFreqChartType] = useState('hbar');

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/equipment', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, abc_data, classes_data, per_eo_data, top50, unplanned_leaders, heatmap, heatmap_eo_stats, frequency } = data;
  // Глобальные настройки (шрифт, размер); _rev для реактивности per-chart палитр
  const _rev = cs._rev;
  const fs = cs.fontSizes;
  const fontFamily = cs.font;

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
    if (typeof av === 'string') return dir * av.localeCompare(bv);
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
    return `rgba(56,189,248,${0.1 + ratio * 0.6})`;
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

  // Заголовки TOP-50 с сортировкой
  const topHeaders = [
    { key: '#', label: '#', sortable: false },
    { key: 'eo', label: 'ЕО', sortable: true },
    { key: 'name', label: 'Наименование', sortable: true },
    { key: 'class_name', label: 'Класс', sortable: true },
    { key: 'n_orders', label: 'Заказов', sortable: true },
    { key: 'plan', label: 'План ₽', sortable: true },
    { key: 'fact', label: 'Факт ₽', sortable: true },
    { key: 'dev', label: 'Откл. ₽', sortable: true },
    { key: '', label: '', sortable: false },
  ];

  /** Цвета ABC — фиксированный массив, синхронизированный с плашками */
  const ABC_FIXED_COLORS = abc_data.map(d => ABC_COLORS[d.abc] || C.dim);

  /** Рендер ABC-графика по типу */
  const renderAbcChart = () => {
    const abcColors = getColorsForChart('eq-abc');
    // Для ABC используем фиксированные цвета по категории, а не палитру
    const cellColors = ABC_FIXED_COLORS;
    const inner = abcChartType === 'pie' ? 0 : 110;
    return (
      <ResponsiveContainer width={420} height={420}>
        <PieChart>
          <Pie data={abc_data} dataKey="sum" nameKey="abc" cx="50%" cy="50%"
            innerRadius={inner} outerRadius={180} paddingAngle={2}
            label={({ name, percent, cx: pcx, cy: pcy, midAngle, outerRadius: oR, startAngle, endAngle }) => {
              const angle = Math.abs(endAngle - startAngle);
              if (angle < 15) return null;
              const radius = oR + 24;
              const x = pcx + radius * Math.cos(-midAngle * RADIAN);
              const y = pcy + radius * Math.sin(-midAngle * RADIAN);
              const displayName = name && name.length > 20 ? name.slice(0, 20) + '...' : name;
              return (
                <text x={x} y={y} fill={C.text} fontSize={11} fontFamily={fontFamily} textAnchor={x > pcx ? 'start' : 'end'} dominantBaseline="central">
                  {displayName} {(percent*100).toFixed(0)}%
                </text>
              );
            }}
            labelLine={{ stroke: C.muted, strokeWidth: 1 }}>
            {abc_data.map((d, i) => (
              <Cell key={i} fill={cellColors[i]} stroke={C.bg} strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontFamily }}
            itemStyle={{ color: C.text }} formatter={v => [`${fmtShort(v)} ₽`]} />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  /** Рендер графика классов по типу */
  const renderClassesChart = () => {
    const clsColors = getColorsForChart('eq-classes');
    const clsMainColor = clsColors[0];
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

  /** Рендер графика частоты по типу */
  const renderFreqChart = () => {
    const freqColors = getColorsForChart('eq-freq');
    const freqMainColor = freqColors[0];
    const freqData = frequency.map(f => ({ ...f, eo_label: f.equipment_name ? `${f.eo} ${f.equipment_name}` : f.eo }));
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
        <KpiCard title="КЛАСС A" value={fmtNum(kpi.abc_a)} color={C.danger} />
        <KpiCard title="КЛАСС B" value={fmtNum(kpi.abc_b)} color={C.warning} />
        <KpiCard title="БЕЗ ЕО (ЗАКАЗОВ)" value={fmtNum(kpi.no_eo_orders)} color={C.dim} />
        <KpiCard title="СРЕДН. ЗАКАЗОВ/ЕО" value={kpi.avg_orders_per_eo} />
      </KpiRow>

      {/* ABC-распределение */}
      {abc_data && abc_data.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>1. ABC-критичность оборудования <ChartSettings chartId="eq-abc" chartTypes={[{value:'donut',label:'Бублик'},{value:'pie',label:'Пирог'}]} currentChartType={abcChartType} onChartTypeChange={setAbcChartType} /></span>}>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ flex: '0 0 auto' }}>
              {renderAbcChart()}
            </div>
            {/* Компактные плашки ABC — цвет синхронизирован с бубликом */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6, minWidth: 220 }}>
              {abc_data.map((d, i) => {
                const clr = ABC_FIXED_COLORS[i];
                return (
                  <div key={d.abc} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 12px', borderRadius: 6, height: 36,
                    background: `${clr}15`,
                    borderLeft: `3px solid ${clr}`,
                  }}>
                    <div style={{ width: 12, height: 12, borderRadius: 2, background: clr, flexShrink: 0 }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: clr, minWidth: 24 }}>{d.abc}</span>
                    <span style={{ fontSize: 12, color: C.text }}>{fmtNum(d.count)} зак.</span>
                    <span style={{ fontSize: 12, color: C.muted, marginLeft: 'auto', whiteSpace: 'nowrap' }}>{fmtShort(d.sum)} ₽ ({d.pct}%)</span>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {/* 2. Таблица классов оборудования */}
      {classes_data.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>2. Классы оборудования — метрики <ChartSettings chartId="eq-classes" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'},{value:'line',label:'Линия'}]} currentChartType={classesChartType} onChartTypeChange={setClassesChartType} /></span>}>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 500px', overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                    {['Класс', 'ЕО', 'Заказов', 'План ₽', 'Факт ₽', 'Откл. ₽'].map(h => (
                      <th key={h} style={{ color: C.muted, fontSize: 11, padding: '8px 10px', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {classes_data.map((r, i) => (
                    <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                      <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px' }}>{r.class_name}</td>
                      <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{fmtNum(r.n_eo)}</td>
                      <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{fmtNum(r.n_orders)}</td>
                      <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.plan)} ₽</td>
                      <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.fact)} ₽</td>
                      <td style={{ color: r.dev > 0 ? C.danger : r.dev < 0 ? C.success : C.muted, fontSize: 12, textAlign: 'right', padding: '6px 10px', fontWeight: 600 }}>
                        {r.dev > 0 ? '+' : ''}{fmtShort(r.dev)} ₽
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ flex: '1 1 380px' }}>
              {renderClassesChart()}
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
                {sortedTop50.map((r, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                    <td style={{ color: C.dim, fontSize: 12, padding: '6px 10px' }}>{i + 1}</td>
                    <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px' }}>{r.eo}</td>
                    <td style={{ color: C.text, fontSize: 12, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px 10px' }}
                      title={r.name}>{r.name}</td>
                    <td style={{ color: C.muted, fontSize: 12, padding: '6px 10px' }}>{r.class_name}</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{r.n_orders}</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.plan)} ₽</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.fact)} ₽</td>
                    <td style={{ color: r.dev > 0 ? C.danger : r.dev < 0 ? C.success : C.muted, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>
                      {r.dev > 0 ? '+' : ''}{fmtShort(r.dev)} ₽
                    </td>
                    <td style={{ padding: '6px 10px' }}><ExcelEoBtn eo={r.eo} /></td>
                  </tr>
                ))}
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
                  {['Класс', 'Внеплановых заказов', 'Факт ₽'].map(h => (
                    <th key={h} style={{ color: C.muted, fontSize: 11, padding: '8px 10px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {unplanned_leaders.map((r, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                    <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px' }}>{r.class_name}</td>
                    <td style={{ color: C.danger, fontSize: 12, textAlign: 'center', fontWeight: 600, padding: '6px 10px' }}>{r.n_orders}</td>
                    <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px 10px' }}>{fmtShort(r.fact)} ₽</td>
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
                        <span>{name.length > 24 ? name.slice(0,24)+'...' : name}</span>
                        <span style={{ color: C.muted, marginLeft: 6 }}>|</span>
                        <span style={{ color: C.accent, marginLeft: 4 }}>{nOrders} зак.</span>
                        <span style={{ color: C.muted, marginLeft: 4 }}>|</span>
                        <span style={{ color: C.warning, marginLeft: 4 }}>{fmtShort(totalFact)} ₽</span>
                      </td>
                      {heatmapMonths.map(m => {
                        const val = heatmapMap[`${eo}|${m}`] || 0;
                        return (
                          <td key={m} style={{ background: heatColor(val), color: val > 0 ? C.text : C.dim, fontSize: 10, textAlign: 'center', padding: '4px 6px' }}>
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
      {frequency.length > 0 && (
        <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>7. Частота обслуживания — средний интервал между заказами (дни) <ChartSettings chartId="eq-freq" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'},{value:'line',label:'Линия'}]} currentChartType={freqChartType} onChartTypeChange={setFreqChartType} /></span>}>
          <div style={{ fontSize: 12, color: C.muted, marginBottom: 8 }}>
            TOP-{frequency.length} ЕО с наименьшим интервалом (только ЕО с 2+ заказами)
          </div>
          {renderFreqChart()}
        </Card>
      )}
    </div>
  );
}
