import React, { useState, useMemo } from 'react';
import { C, heatBg } from '../theme/arctic';

/**
 * Heatmap-таблица с RGB-градиентным фоном строк.
 * Опционально: сортировка по столбцам, аккордеон с заказами + пагинация.
 */

function fmtShort(val) {
  if (!val && val !== 0) return "0";
  const abs = Math.abs(val);
  const sign = val >= 0 ? "" : "-";
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(1)}Млрд`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(1)}М`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(1)}К`;
  return `${sign}${abs.toFixed(0)}`;
}

const PAGE_BTN = {
  padding: '4px 12px',
  background: C.bg,
  border: `1px solid ${C.border}`,
  borderRadius: 6,
  color: C.accent,
  cursor: 'pointer',
  fontSize: 11,
};

const COLUMNS = [
  { key: 'name', label: 'Наименование', align: 'left' },
  { key: 'plan', label: 'План', align: 'right' },
  { key: 'fact', label: 'Факт', align: 'right' },
  { key: 'dev',  label: 'Отклонение', align: 'right' },
  { key: 'count', label: 'Заказов', align: 'center' },
];

const INNER_COLUMNS = [
  { key: 'id',         label: 'Заказ',      align: 'left',  type: 'str' },
  { key: 'date_start', label: 'Дата нач.',  align: 'left',  type: 'str' },
  { key: 'date_end',   label: 'Дата кон.',  align: 'left',  type: 'str' },
  { key: 'vid',        label: 'Вид работ',  align: 'left',  type: 'str' },
  { key: 'stat',       label: 'Статус',     align: 'left',  type: 'str' },
  { key: 'text',       label: 'Текст работ',align: 'left',  type: 'str' },
  { key: 'plan',       label: 'План ₽',     align: 'right', type: 'num' },
  { key: 'fact',       label: 'Факт ₽',     align: 'right', type: 'num' },
];

/** Цвет даты по источнику каскада */
function dateColor(source) {
  if (source === 'FACT') return '#ffffff';
  if (source === 'PLAN') return '#fbbf24';
  return '#f43f5e';
}

export default function HeatmapTable({
  data,
  nameKey = "name",
  expandable = false,
  expandedName = null,
  onToggleExpand = null,
  expandedOrders = [],
  expandedTotal = 0,
  expandedLoading = false,
  expandedPage = 1,
  onPageChange = null,
  onExportExcel = null,
  pageSize = 20,
}) {
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('desc');
  // Сортировка внутри раскрытого списка заказов
  const [innerSortCol, setInnerSortCol] = useState(null);
  const [innerSortDir, setInnerSortDir] = useState('desc');

  if (!data || data.length === 0) return <p style={{ color: C.muted }}>Нет данных</p>;

  const handleSort = (colKey) => {
    if (sortCol === colKey) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(colKey);
      setSortDir(colKey === 'name' ? 'asc' : 'desc');
    }
  };

  const sortedData = useMemo(() => {
    if (!sortCol) return data;
    const sorted = [...data].sort((a, b) => {
      const ak = sortCol === 'name' ? (a[nameKey] || '') : (a[sortCol] || 0);
      const bk = sortCol === 'name' ? (b[nameKey] || '') : (b[sortCol] || 0);
      if (sortCol === 'name') {
        return sortDir === 'asc' ? String(ak).localeCompare(String(bk), 'ru') : String(bk).localeCompare(String(ak), 'ru');
      }
      return sortDir === 'asc' ? ak - bk : bk - ak;
    });
    return sorted;
  }, [data, sortCol, sortDir, nameKey]);

  const handleInnerSort = (colKey) => {
    if (innerSortCol === colKey) {
      setInnerSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setInnerSortCol(colKey);
      const col = INNER_COLUMNS.find(c => c.key === colKey);
      setInnerSortDir(col && col.type === 'num' ? 'desc' : 'asc');
    }
  };

  const sortedOrders = useMemo(() => {
    if (!innerSortCol || !expandedOrders.length) return expandedOrders;
    const col = INNER_COLUMNS.find(c => c.key === innerSortCol);
    return [...expandedOrders].sort((a, b) => {
      const av = a[innerSortCol] || (col?.type === 'num' ? 0 : '');
      const bv = b[innerSortCol] || (col?.type === 'num' ? 0 : '');
      if (col?.type === 'num') return innerSortDir === 'asc' ? av - bv : bv - av;
      return innerSortDir === 'asc' ? String(av).localeCompare(String(bv), 'ru') : String(bv).localeCompare(String(av), 'ru');
    });
  }, [expandedOrders, innerSortCol, innerSortDir]);

  const absMax = Math.max(...data.map(d => Math.abs(d.dev || 0)), 1);
  const totalPages = Math.ceil(expandedTotal / pageSize);

  const sortArrow = (colKey) => {
    if (sortCol !== colKey) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
  };

  return (
    <div style={{ overflowX: 'auto', borderRadius: 8, border: `1px solid ${C.border}` }}>
      <table>
        <thead>
          <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
            {COLUMNS.map(col => (
              <th key={col.key}
                onClick={expandable ? () => handleSort(col.key) : undefined}
                style={{
                  color: sortCol === col.key ? C.accent : C.muted,
                  fontSize: 12,
                  textAlign: col.align,
                  cursor: expandable ? 'pointer' : 'default',
                  userSelect: 'none',
                  whiteSpace: 'nowrap',
                }}
                title={expandable ? `Сортировать по: ${col.label}` : undefined}
              >
                {col.label}{expandable && sortArrow(col.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, i) => {
            const { bg, tc } = heatBg(row.dev || 0, absMax);
            const sign = row.dev > 0 ? "+" : "";
            const isExpanded = expandable && expandedName === row[nameKey];

            const mainRow = (
              <tr key={i} style={{ background: bg, borderBottom: `1px solid ${C.border}33` }}>
                <td
                  style={{
                    color: C.text, fontSize: 13, maxWidth: 350, overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    cursor: expandable ? 'pointer' : 'default',
                  }}
                  title={expandable ? `${row[nameKey]} — нажмите для детализации` : row[nameKey]}
                  onClick={expandable && onToggleExpand ? () => onToggleExpand(row[nameKey]) : undefined}
                >
                  {expandable && (isExpanded ? '▼ ' : '▶ ')}
                  {i + 1}. {row[nameKey]}
                </td>
                <td style={{ color: '#e0e0e0', textAlign: 'right', fontSize: 13 }}>{fmtShort(row.plan)} ₽</td>
                <td style={{ color: '#e0e0e0', textAlign: 'right', fontSize: 13 }}>{fmtShort(row.fact)} ₽</td>
                <td style={{ color: tc, textAlign: 'right', fontSize: 14, fontWeight: 600 }}>{sign}{fmtShort(row.dev)} ₽</td>
                <td style={{ color: '#ccc', textAlign: 'center', fontSize: 13 }}>{row.count}</td>
              </tr>
            );

            if (!expandable) return mainRow;

            return (
              <React.Fragment key={i}>
                {mainRow}
                {isExpanded && (
                  <tr>
                    <td colSpan={5} style={{ padding: 0 }}>
                      <div style={{
                        background: 'linear-gradient(145deg, #1e293b 0%, #1a2332 100%)',
                        padding: '12px 16px',
                        borderLeft: `3px solid ${C.accent}`,
                        margin: '0 8px 8px 8px',
                        borderRadius: '0 0 8px 8px',
                      }}>
                        {expandedLoading ? (
                          <p style={{ color: C.muted, fontSize: 12 }}>Загрузка заказов...</p>
                        ) : expandedOrders.length === 0 ? (
                          <p style={{ color: C.muted, fontSize: 12 }}>Нет заказов</p>
                        ) : (
                          <>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                              <span style={{ fontSize: 10, color: C.dim }}>
                                <span style={{ color: '#ffffff' }}>белый</span> — факт, <span style={{ color: '#fbbf24' }}>жёлтый •</span> — план, <span style={{ color: '#f43f5e' }}>красный</span> — нет
                              </span>
                              {onExportExcel && (
                                <button
                                  onClick={() => onExportExcel(row[nameKey])}
                                  style={{ ...PAGE_BTN, fontSize: 10 }}
                                  title="Выгрузить все заказы в Excel"
                                >Excel</button>
                              )}
                            </div>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                              <thead>
                                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                                  {INNER_COLUMNS.map(col => (
                                    <th key={col.key}
                                      onClick={() => handleInnerSort(col.key)}
                                      style={{
                                        color: innerSortCol === col.key ? C.accent : C.dim,
                                        fontSize: 10, padding: '4px 8px',
                                        textAlign: col.align, fontWeight: 600,
                                        cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap',
                                      }}
                                      title={`Сортировать по: ${col.label}`}
                                    >
                                      {col.label}{innerSortCol === col.key ? (innerSortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {sortedOrders.map((ord, j) => {
                                  const dClr = dateColor(ord.date_source);
                                  const planMark = ord.date_source === 'PLAN' ? ' \u2022' : '';
                                  return (
                                  <tr key={j} style={{ borderBottom: `1px solid ${C.border}22` }}>
                                    <td style={{ color: C.accent, fontSize: 11, padding: '4px 8px', fontWeight: 600 }}>{ord.id}</td>
                                    <td style={{ color: dClr, fontSize: 11, padding: '4px 8px', whiteSpace: 'nowrap' }}>{ord.date_start ? ord.date_start + planMark : '—'}</td>
                                    <td style={{ color: dClr, fontSize: 11, padding: '4px 8px', whiteSpace: 'nowrap' }}>{ord.date_end ? ord.date_end + planMark : '—'}</td>
                                    <td style={{ color: C.text, fontSize: 11, padding: '4px 8px' }}>{ord.vid}</td>
                                    <td style={{ color: C.muted, fontSize: 11, padding: '4px 8px' }}>{ord.stat}</td>
                                    <td style={{
                                      color: C.text, fontSize: 11, padding: '4px 8px',
                                      maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                    }} title={ord.text}>{ord.text}</td>
                                    <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', textAlign: 'right' }}>{fmtShort(ord.plan)}</td>
                                    <td style={{ color: C.text, fontSize: 11, padding: '4px 8px', textAlign: 'right' }}>{fmtShort(ord.fact)}</td>
                                  </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                            {expandedTotal > pageSize && (
                              <div style={{
                                display: 'flex', justifyContent: 'space-between',
                                alignItems: 'center', marginTop: 8, paddingTop: 8,
                                borderTop: `1px solid ${C.border}33`,
                              }}>
                                <span style={{ color: C.muted, fontSize: 11 }}>
                                  {((expandedPage - 1) * pageSize) + 1}–{Math.min(expandedPage * pageSize, expandedTotal)} из {expandedTotal}
                                </span>
                                <div style={{ display: 'flex', gap: 4 }}>
                                  <button
                                    disabled={expandedPage <= 1}
                                    onClick={() => onPageChange && onPageChange(expandedPage - 1)}
                                    style={{ ...PAGE_BTN, opacity: expandedPage <= 1 ? 0.3 : 1 }}
                                  >← Назад</button>
                                  <button
                                    disabled={expandedPage >= totalPages}
                                    onClick={() => onPageChange && onPageChange(expandedPage + 1)}
                                    style={{ ...PAGE_BTN, opacity: expandedPage >= totalPages ? 0.3 : 1 }}
                                  >Вперёд →</button>
                                </div>
                              </div>
                            )}
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
  );
}
