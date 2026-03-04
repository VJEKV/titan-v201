import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList } from 'recharts';
import { C } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet, apiDownload } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import HeatmapTable from '../components/HeatmapTable';
import Card from '../components/Card';
import ChartSettings, { useChartSettings } from '../components/ChartSettings';
import DonutWithLegend from '../components/DonutWithLegend';
import DateFootnote from '../components/DateFootnote';

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

export default function Workplaces() {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const csDonut = useChartSettings('wp-donut');
  const csBar = useChartSettings('wp-bar');

  // Типы графиков
  const [barType, setBarType] = useState('hbar');

  // Аккордеон РМ (общий для перерасхода и экономии)
  const [rmExpanded, setRmExpanded] = useState(null);
  const [rmOrders, setRmOrders] = useState([]);
  const [rmTotal, setRmTotal] = useState(0);
  const [rmPage, setRmPage] = useState(1);
  const [rmLoading, setRmLoading] = useState(false);
  const [rmSort, setRmSort] = useState({ col: 'date_start', dir: 'desc' });

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/workplaces', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
    setRmExpanded(null); setRmOrders([]); setRmPage(1); setRmSort({ col: 'date_start', dir: 'desc' });
  }, [sessionId, filters, thresholds]);

  const fetchRmOrders = (name, page, sort = rmSort) => {
    setRmLoading(true);
    apiGet('/api/workplaces/orders', {
      session_id: sessionId, filters, thresholds,
      rm: name, page, page_size: 20,
      sort_by: sort.col, sort_dir: sort.dir,
    })
      .then(res => { setRmOrders(res.orders || []); setRmTotal(res.total || 0); })
      .catch(() => { setRmOrders([]); setRmTotal(0); })
      .finally(() => setRmLoading(false));
  };
  const toggleRmExpand = (name) => {
    if (rmExpanded === name) { setRmExpanded(null); setRmOrders([]); setRmTotal(0); setRmPage(1); return; }
    const s = { col: 'date_start', dir: 'desc' }; setRmSort(s);
    setRmExpanded(name); setRmPage(1); fetchRmOrders(name, 1, s);
  };
  const handleRmPage = (p) => { setRmPage(p); fetchRmOrders(rmExpanded, p); };
  const handleRmSortChange = (col, dir) => {
    const s = { col, dir }; setRmSort(s); setRmPage(1); fetchRmOrders(rmExpanded, 1, s);
  };

  const exportRmExcel = (name) => {
    apiDownload('/api/export/orders_excel', {
      session_id: sessionId, filters, thresholds, group_by: 'rm', group_value: name,
    }).catch(() => alert('Ошибка при выгрузке Excel'));
  };

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, rm_data } = data;
  const overrun = rm_data.filter(d => d.dev > 0);
  const savings = rm_data.filter(d => d.dev < 0);
  const sortedByCount = [...rm_data].sort((a, b) => b.count - a.count).slice(0, 15);
  const fsz = csDonut.fontSizes;
  const fontFamily = csDonut.font;

  /** Данные для DonutWithLegend */
  const donutSlice = rm_data.slice(0, 10);
  const donutData = donutSlice.map(d => ({ name: d.name, value: d.fact, count: d.count, pct: null }));
  const donutColors = csDonut.paletteColors;

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
    return (
      <ResponsiveContainer width="100%" height={Math.max(400, sortedByCount.length * 40)}>
        <BarChart data={sortedByCount} layout="vertical">
          <XAxis type="number" tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }} />
          <YAxis type="category" dataKey="name" width={220} tick={{ fill: C.muted, fontSize: fsz.tick, fontFamily }}
            tickFormatter={v => v.length > 30 ? v.slice(0,30)+'...' : v} />
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
      <DateFootnote />
      <SectionTitle sub="Кто сколько потратил, перерасход, количество заказов и ЕО">Аналитика по рабочим местам</SectionTitle>

      <KpiRow>
        <KpiCard title="РАБОЧИХ МЕСТ" value={kpi.rm_count} />
        <KpiCard title="ЗАКАЗОВ (Σ)" value={kpi.total_orders} />
        <KpiCard title="ФАКТ (Σ)" value={`${fmtShort(kpi.total_fact)} ₽`} />
        <KpiCard title="С ПЕРЕРАСХОДОМ" value={`${kpi.overrun_count} РМ`} color={C.warning} />
      </KpiRow>

{/* Сводная — бублик */}
      <Card title="1. Сводная аналитика">
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 500px' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
              <ChartSettings chartId="wp-donut" />
            </div>
            <DonutWithLegend
              data={donutData}
              colors={donutColors}
              chartId="wp-donut"
              fontSize={fsz.pie || 12}
              fontFamily={fontFamily}
            />
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
          <HeatmapTable data={overrun.slice(0, 15)} expandable
            expandedName={rmExpanded} onToggleExpand={toggleRmExpand}
            expandedOrders={rmOrders} expandedTotal={rmTotal}
            expandedLoading={rmLoading} expandedPage={rmPage}
            onPageChange={handleRmPage} onExportExcel={exportRmExcel}
            onInnerSortChange={handleRmSortChange} />
        </Card>
      )}

      {/* Экономия */}
      {savings.length > 0 && (
        <Card title="3. РМ с экономией" borderColor={C.success}>
          <HeatmapTable data={savings.slice(0, 15)} expandable
            expandedName={rmExpanded} onToggleExpand={toggleRmExpand}
            expandedOrders={rmOrders} expandedTotal={rmTotal}
            expandedLoading={rmLoading} expandedPage={rmPage}
            onPageChange={handleRmPage} onExportExcel={exportRmExcel}
            onInnerSortChange={handleRmSortChange} />
        </Card>
      )}
    </div>
  );
}
