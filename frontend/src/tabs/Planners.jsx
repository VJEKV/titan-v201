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
  const [donutType, setDonutType] = useState('donut');
  const [barType, setBarType] = useState('hbar');

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/planners', { session_id: sessionId, filters, thresholds })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, ingrp_data, users_data, user_scoring } = data;
  const sortedIngrp = [...ingrp_data].sort((a, b) => b.count - a.count);
  const fsz = csDonut.fontSizes;
  const fontFamily = csDonut.font;

  /** Экспорт скоринга в Excel */
  const exportScoringExcel = () => {
    const header = ['#', 'Пользователь', 'Заказов', 'Score %', ...Object.keys(FIELD_SAP_MAP)];
    const rows = (user_scoring || []).map((u, i) => {
      const fields = Object.keys(FIELD_SAP_MAP).map(f => {
        const info = u.empty_fields[f];
        return info ? `${info.count} (${info.pct}%)` : '—';
      });
      return [i + 1, u.user, u.total_orders, `${u.score}%`, ...fields];
    });
    const legendHeader = ['Плашка', 'Поле SAP', 'Описание'];
    const legendRows = Object.entries(FIELD_SAP_MAP).map(([name, info]) => [name, info.sap, info.tip]);
    const dataSheet = [header, ...rows].map(r => r.join('\t')).join('\n');
    const legendSheet = [legendHeader, ...legendRows].map(r => r.join('\t')).join('\n');
    const csv = `СКОРИНГ ПОЛЬЗОВАТЕЛЕЙ\n${dataSheet}\n\n\nЛЕГЕНДА (поля SAP)\n${legendSheet}`;
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `Скоринг_плановиков_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  /** Рендер бублика/пирога */
  const renderDonut = () => {
    const colors = csDonut.paletteColors;
    const inner = donutType === 'pie' ? 0 : 140;
    const sliceData = ingrp_data.slice(0, 10);
    const RADIAN = Math.PI / 180;
    const showLabels = sliceData.length <= 5;
    return (
      <ResponsiveContainer width="100%" height={620}>
        <PieChart>
          <Pie data={sliceData} dataKey="fact" nameKey="name" cx="50%" cy="50%"
            innerRadius={inner} outerRadius={230} paddingAngle={2}
            label={showLabels ? ({ name, percent, cx: pcx, cy: pcy, midAngle, outerRadius: oR, startAngle, endAngle }) => {
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
            labelLine={showLabels ? { stroke: C.muted, strokeWidth: 1 } : false}>
            {sliceData.map((_, i) => (
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
        <HeatmapTable data={ingrp_data} />
      </Card>

      {/* Сводная — бублик */}
      <Card title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>Сводная по группам <ChartSettings chartId="pl-donut" chartTypes={[{value:'donut',label:'Бублик'},{value:'pie',label:'Пирог'}]} currentChartType={donutType} onChartTypeChange={setDonutType} /></span>}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 500px' }}>
            {renderDonut()}
            {/* Компактная легенда */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 8 }}>
              {ingrp_data.slice(0, 10).map((d, i) => {
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
              <ChartSettings chartId="pl-bar" chartTypes={[{value:'hbar',label:'Горизонт.'},{value:'vbar',label:'Вертикал.'}]} currentChartType={barType} onChartTypeChange={setBarType} />
            </div>
            {renderSideBar()}
          </div>
        </div>
      </Card>

      {/* Авторы */}
      {users_data.length > 0 && (
        <Card title="2. Авторы заказов (USER) — TOP-20">
          <HeatmapTable data={users_data} />
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
