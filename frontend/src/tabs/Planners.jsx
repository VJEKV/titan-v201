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

/** Маппинг полей SAP */
const FIELD_SAP_MAP = {
  'План. стоимость': { sap: 'PLAN_COST (План. стоимость заказа)', tip: 'Поле SAP: плановая стоимость заказа. Пустое поле означает что заказ создан без бюджета.' },
  'Дата начала': { sap: 'GSTRP (Базовая дата начала)', tip: 'Поле SAP: базовая дата начала заказа. Отсутствие — ошибка планирования.' },
  'Дата окончания': { sap: 'GLTRP (Базовая дата окончания)', tip: 'Поле SAP: базовая дата окончания заказа.' },
  'Техническое место': { sap: 'TPLNR (Техническое место)', tip: 'Поле SAP: код технического места привязки заказа.' },
  'Оборудование': { sap: 'EQUNR (Единица оборудования)', tip: 'Поле SAP: код единицы оборудования. Пустое — заказ без привязки к ЕО.' },
  'Код ABC': { sap: 'ABC (Классификатор критичности)', tip: 'Поле SAP: категория критичности оборудования (A/B/C).' },
  'Вид заказа': { sap: 'AUART (Вид заказа)', tip: 'Поле SAP: тип заказа (плановый/внеплановый ремонт).' },
  'Номер договора': { sap: 'EBELN (Номер договора)', tip: 'Поле SAP: привязка к договору на выполнение работ.' },
};

export default function Planners() {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hoveredField, setHoveredField] = useState(null);
  const csDonut = useChartSettings('pl-donut');
  const csBar = useChartSettings('pl-bar');

  // Типы графиков
  const [barType, setBarType] = useState('hbar');

  // Аккордеон INGRP
  const [ingrpExpanded, setIngrpExpanded] = useState(null);
  const [ingrpOrders, setIngrpOrders] = useState([]);
  const [ingrpTotal, setIngrpTotal] = useState(0);
  const [ingrpPage, setIngrpPage] = useState(1);
  const [ingrpLoading, setIngrpLoading] = useState(false);
  const [ingrpSort, setIngrpSort] = useState({ col: 'date_start', dir: 'desc' });

  // Аккордеон USER
  const [userExpanded, setUserExpanded] = useState(null);
  const [userOrders, setUserOrders] = useState([]);
  const [userTotal, setUserTotal] = useState(0);
  const [userPage, setUserPage] = useState(1);
  const [userLoading, setUserLoading] = useState(false);
  const [userSort, setUserSort] = useState({ col: 'date_start', dir: 'desc' });

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/planners', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
    setIngrpExpanded(null); setIngrpOrders([]); setIngrpPage(1); setIngrpSort({ col: 'date_start', dir: 'desc' });
    setUserExpanded(null); setUserOrders([]); setUserPage(1); setUserSort({ col: 'date_start', dir: 'desc' });
  }, [sessionId, filters, thresholds]);

  const fetchIngrpOrders = (name, page, sort = ingrpSort) => {
    setIngrpLoading(true);
    apiGet('/api/planners/orders', {
      session_id: sessionId, filters, thresholds,
      ingrp: name, page, page_size: 20,
      sort_by: sort.col, sort_dir: sort.dir,
    })
      .then(res => { setIngrpOrders(res.orders || []); setIngrpTotal(res.total || 0); })
      .catch(() => { setIngrpOrders([]); setIngrpTotal(0); })
      .finally(() => setIngrpLoading(false));
  };
  const toggleIngrpExpand = (name) => {
    if (ingrpExpanded === name) { setIngrpExpanded(null); setIngrpOrders([]); setIngrpTotal(0); setIngrpPage(1); return; }
    const s = { col: 'date_start', dir: 'desc' }; setIngrpSort(s);
    setIngrpExpanded(name); setIngrpPage(1); fetchIngrpOrders(name, 1, s);
  };
  const handleIngrpPage = (p) => { setIngrpPage(p); fetchIngrpOrders(ingrpExpanded, p); };
  const handleIngrpSortChange = (col, dir) => {
    const s = { col, dir }; setIngrpSort(s); setIngrpPage(1); fetchIngrpOrders(ingrpExpanded, 1, s);
  };

  const fetchUserOrders = (name, page, sort = userSort) => {
    setUserLoading(true);
    apiGet('/api/planners/user_orders', {
      session_id: sessionId, filters, thresholds,
      user: name, page, page_size: 20,
      sort_by: sort.col, sort_dir: sort.dir,
    })
      .then(res => { setUserOrders(res.orders || []); setUserTotal(res.total || 0); })
      .catch(() => { setUserOrders([]); setUserTotal(0); })
      .finally(() => setUserLoading(false));
  };
  const toggleUserExpand = (name) => {
    if (userExpanded === name) { setUserExpanded(null); setUserOrders([]); setUserTotal(0); setUserPage(1); return; }
    const s = { col: 'date_start', dir: 'desc' }; setUserSort(s);
    setUserExpanded(name); setUserPage(1); fetchUserOrders(name, 1, s);
  };
  const handleUserPage = (p) => { setUserPage(p); fetchUserOrders(userExpanded, p); };
  const handleUserSortChange = (col, dir) => {
    const s = { col, dir }; setUserSort(s); setUserPage(1); fetchUserOrders(userExpanded, 1, s);
  };

  const exportIngrpExcel = (name) => {
    apiDownload('/api/export/orders_excel', {
      session_id: sessionId, filters, thresholds, group_by: 'ingrp', group_value: name,
    }).catch(() => alert('Ошибка при выгрузке Excel'));
  };
  const exportUserExcel = (name) => {
    apiDownload('/api/export/orders_excel', {
      session_id: sessionId, filters, thresholds, group_by: 'user', group_value: name,
    }).catch(() => alert('Ошибка при выгрузке Excel'));
  };

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, ingrp_data, users_data, user_scoring } = data;
  const sortedIngrp = [...ingrp_data].sort((a, b) => b.count - a.count);
  const fsz = csDonut.fontSizes;
  const fontFamily = csDonut.font;

  /** Экспорт скоринга в Excel (через бэкенд) */
  const exportScoringExcel = () => {
    apiDownload('/api/planners/scoring_excel', {
      session_id: sessionId, filters, thresholds,
    }).catch(err => {
      console.error('Ошибка экспорта:', err);
      alert('Ошибка при выгрузке Excel. Попробуйте ещё раз.');
    });
  };

  /** Данные для DonutWithLegend */
  const donutSlice = ingrp_data.slice(0, 10);
  const donutData = donutSlice.map(d => ({ name: d.name, value: d.fact, count: d.count, pct: null }));
  const donutColors = csDonut.paletteColors;

  /** Рендер бокового бар-чарта */
  const renderSideBar = () => {
    const barMainColor = csBar.paletteColors[0];
    if (barType === 'vbar') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={sortedIngrp}>
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
      <ResponsiveContainer width="100%" height={Math.max(350, sortedIngrp.length * 35)}>
        <BarChart data={sortedIngrp} layout="vertical">
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
      <SectionTitle sub="Кто сколько потратил, перерасход, количество заказов">Аналитика по плановикам</SectionTitle>

      <KpiRow>
        <KpiCard title="ГРУПП ПЛАНОВИКОВ" value={kpi.n_ingrp} />
        <KpiCard title="АВТОРОВ (USER)" value={kpi.n_users} />
        <KpiCard title="ФАКТ (Σ)" value={`${fmtShort(kpi.total_fact)} ₽`} />
        <KpiCard title="С ПЕРЕРАСХОДОМ" value={`${kpi.overrun_count} зак.`} color={C.warning} />
      </KpiRow>

      {/* Группы */}
      <Card title="1. Группы плановиков (INGRP)">
        <HeatmapTable data={ingrp_data} expandable
          expandedName={ingrpExpanded} onToggleExpand={toggleIngrpExpand}
          expandedOrders={ingrpOrders} expandedTotal={ingrpTotal}
          expandedLoading={ingrpLoading} expandedPage={ingrpPage}
          onPageChange={handleIngrpPage} onExportExcel={exportIngrpExcel}
          onInnerSortChange={handleIngrpSortChange} />
      </Card>

{/* Сводная — бублик */}
      <Card title="Сводная по группам">
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 500px' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
              <ChartSettings chartId="pl-donut" />
            </div>
            <DonutWithLegend
              data={donutData}
              colors={donutColors}
              chartId="pl-donut"
              fontSize={fsz.pie || 12}
              fontFamily={fontFamily}
            />
          </div>
          <div style={{ flex: '1 1 380px' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
              <ChartSettings chartId="pl-bar" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'}]} currentChartType={barType} onChartTypeChange={setBarType} />
            </div>
            {renderSideBar()}
          </div>
        </div>
      </Card>

      {/* Авторы */}
      {users_data.length > 0 && (
        <Card title="2. Авторы заказов (USER) — TOP-20">
          <HeatmapTable data={users_data} expandable
            expandedName={userExpanded} onToggleExpand={toggleUserExpand}
            expandedOrders={userOrders} expandedTotal={userTotal}
            expandedLoading={userLoading} expandedPage={userPage}
            onPageChange={handleUserPage} onExportExcel={exportUserExcel}
            onInnerSortChange={handleUserSortChange} />
        </Card>
      )}

      {/* Скоринг пользователей */}
      {user_scoring && user_scoring.length > 0 && (
        <Card title="3. Скоринг пользователей: незаполненные поля" borderColor={C.warning}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: C.muted, flex: 1 }}>
              Показаны пользователи с наибольшим процентом незаполненных полей в заказах.
              Чем выше Score — тем хуже качество заполнения. Наведите на плашку для описания поля SAP.
            </div>
            <button onClick={exportScoringExcel} style={{
              padding: '6px 14px', background: C.bg, border: `1px solid ${C.border}`,
              borderRadius: 6, color: C.accent, cursor: 'pointer', fontSize: 12, whiteSpace: 'nowrap', marginLeft: 12,
            }}>
              Выгрузить в Excel
            </button>
          </div>
          <div style={{ overflowX: 'auto', borderRadius: 8, border: `1px solid ${C.border}` }}>
            <table>
              <thead>
                <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                  <th style={{ color: C.muted, fontSize: 11, padding: '8px 10px' }}>#</th>
                  <th style={{ color: C.muted, fontSize: 11, padding: '8px 10px' }}>Пользователь</th>
                  <th style={{ color: C.muted, fontSize: 11, padding: '8px 10px', textAlign: 'center' }}>Заказов</th>
                  <th style={{ color: C.muted, fontSize: 11, padding: '8px 10px', textAlign: 'center' }}>Score %</th>
                  <th style={{ color: C.muted, fontSize: 11, padding: '8px 10px' }}>Незаполненные поля</th>
                </tr>
              </thead>
              <tbody>
                {user_scoring.map((u, i) => {
                  const scoreColor = u.score > 30 ? C.danger : u.score > 15 ? C.warning : C.success;
                  return (
                    <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                      <td style={{ color: C.dim, fontSize: 12, padding: '6px 10px' }}>{i + 1}</td>
                      <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px 10px' }}>{u.user}</td>
                      <td style={{ color: C.text, fontSize: 12, textAlign: 'center', padding: '6px 10px' }}>{u.total_orders}</td>
                      <td style={{ textAlign: 'center', padding: '6px 10px' }}>
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: 4,
                          fontSize: 12, fontWeight: 600, color: scoreColor,
                          background: `${scoreColor}15`, border: `1px solid ${scoreColor}40`,
                        }}>
                          {u.score}%
                        </span>
                      </td>
                      <td style={{ padding: '6px 10px' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {Object.entries(u.empty_fields).map(([field, info]) => {
                            const sapInfo = FIELD_SAP_MAP[field];
                            return (
                              <span key={field}
                                onMouseEnter={() => setHoveredField(field)}
                                onMouseLeave={() => setHoveredField(null)}
                                title={sapInfo ? sapInfo.tip : field}
                                style={{
                                  display: 'inline-block', padding: '2px 6px', borderRadius: 4,
                                  fontSize: 10, cursor: 'help', position: 'relative',
                                  color: info.pct > 50 ? C.danger : C.warning,
                                  background: `${info.pct > 50 ? C.danger : C.warning}10`,
                                  border: `1px solid ${info.pct > 50 ? C.danger : C.warning}30`,
                                }}>
                                {field}: {info.count} ({info.pct}%)
                              </span>
                            );
                          })}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {/* Сноска с описанием полей SAP */}
          <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: `${C.accent}08`, border: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.accent, marginBottom: 6 }}>Справка по полям SAP</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 4 }}>
              {Object.entries(FIELD_SAP_MAP).map(([name, info]) => (
                <div key={name} style={{ fontSize: 11, color: C.muted }}>
                  <strong style={{ color: C.text }}>{name}</strong> — {info.sap}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
