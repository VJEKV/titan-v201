import { useState, useEffect, useCallback } from 'react';
import { C } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet, apiDownload } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import Badge from '../components/Badge';
import Card from '../components/Card';
import TagSelect from '../components/TagSelect';
import DateFootnote from '../components/DateFootnote';
import StarButton from '../components/StarButton';
import { useStarred } from '../hooks/useStarred';

function fmtShort(v) {
  if (!v && v !== 0) return "—";
  const a = Math.abs(v), s = v >= 0 ? "" : "-";
  if (a >= 1e6) return `${s}${(a/1e6).toFixed(1)}М`;
  if (a >= 1e3) return `${s}${(a/1e3).toFixed(1)}К`;
  return `${s}${a.toFixed(0)}`;
}

function fmtNum(v) {
  if (!v && v !== 0) return "—";
  return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

export default function Orders({ activeMethod, setActiveMethod }) {
  const { debouncedFilters, debouncedThresholds, sessionId, filters, thresholds } = useFilters();
  const { starredOrders, starredEO, toggleOrder, toggleEO, isOrderStarred, isEOStarred, clearAll, totalStarred } = useStarred();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState('Risk_Sum');
  const [order, setOrder] = useState('desc');

  // Фильтр по избранному
  const [starredActive, setStarredActive] = useState(false);

  // Быстрые фильтры
  const [qf, setQf] = useState({ author: [], tm: [], method: [], ceh: [], zavod: [], rm: [], eo: [], order_ids: [], eo_codes: [] });
  const [appliedQf, setAppliedQf] = useState({ author: [], tm: [], method: [], ceh: [], zavod: [], rm: [], eo: [], order_ids: [], eo_codes: [] });
  const [orderIdInput, setOrderIdInput] = useState('');

  // Расширенный поиск ЕО
  const [eoSearchQuery, setEoSearchQuery] = useState('');
  const [eoSearchResults, setEoSearchResults] = useState([]);
  const [eoSearchLoading, setEoSearchLoading] = useState(false);
  const [eoTags, setEoTags] = useState([]); // [{code, name}]

  const updateQf = (key, vals) => setQf(prev => ({ ...prev, [key]: vals }));

  // Поиск ЕО по названию и коду
  useEffect(() => {
    if (!sessionId || eoSearchQuery.trim().length < 1) {
      setEoSearchResults([]);
      return;
    }
    const timer = setTimeout(() => {
      setEoSearchLoading(true);
      apiGet('/api/equipment/search', { session_id: sessionId, q: eoSearchQuery.trim() })
        .then(res => setEoSearchResults(res.results || []))
        .catch(() => setEoSearchResults([]))
        .finally(() => setEoSearchLoading(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [sessionId, eoSearchQuery]);

  // Добавить тег ЕО
  const addEoTag = (item) => {
    if (eoTags.some(t => t.code === item.code)) return;
    const newTags = [...eoTags, item];
    setEoTags(newTags);
    setEoSearchQuery('');
    setEoSearchResults([]);
    // Обновляем eo_codes в quick_filters
    setQf(prev => ({ ...prev, eo_codes: newTags.map(t => t.code) }));
  };

  // Удалить тег ЕО
  const removeEoTag = (code) => {
    const newTags = eoTags.filter(t => t.code !== code);
    setEoTags(newTags);
    setQf(prev => ({ ...prev, eo_codes: newTags.map(t => t.code) }));
  };

  // Автоустановка фильтра при переходе с вкладки Риски
  useEffect(() => {
    if (activeMethod) {
      setQf(prev => ({ ...prev, method: [activeMethod] }));
      setAppliedQf(prev => ({ ...prev, method: [activeMethod] }));
      if (setActiveMethod) setActiveMethod(null);
    }
  }, [activeMethod]);

  // Добавить номера заказов из текстового ввода
  const addOrderIds = () => {
    if (!orderIdInput.trim()) return;
    const newIds = orderIdInput.split(',').map(s => s.trim()).filter(Boolean);
    const merged = [...new Set([...qf.order_ids, ...newIds])];
    setQf(prev => ({ ...prev, order_ids: merged }));
    setOrderIdInput('');
  };

  const applyQuickFilters = () => {
    setAppliedQf({ ...qf });
    setPage(1);
  };

  const resetQuickFilters = () => {
    const empty = { author: [], tm: [], method: [], ceh: [], zavod: [], rm: [], eo: [], order_ids: [], eo_codes: [] };
    setQf(empty);
    setAppliedQf(empty);
    setEoTags([]);
    setEoSearchQuery('');
    setPage(1);
  };

  // Формируем фильтры с quick_filters
  const buildFilters = useCallback(() => {
    const hasQf = Object.values(appliedQf).some(v => v.length > 0);
    let result = filters;
    if (hasQf) {
      result = { ...result, quick_filters: appliedQf };
    }
    if (starredActive && totalStarred > 0) {
      result = { ...result, starred_orders: [...starredOrders], starred_eo: [...starredEO] };
    }
    return result;
  }, [debouncedFilters, appliedQf, starredActive, starredOrders, starredEO, totalStarred]);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/orders', {
      session_id: sessionId, filters: buildFilters(), debouncedThresholds,
      page, page_size: 50, sort, order,
    })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, debouncedFilters, debouncedThresholds, page, sort, order, appliedQf, starredActive, starredOrders, starredEO]);

  if (loading) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const handleSort = (col) => {
    if (sort === col) {
      setOrder(order === 'desc' ? 'asc' : 'desc');
    } else {
      setSort(col);
      setOrder('desc');
    }
    setPage(1);
  };

  const columns = [
    { key: 'ID', label: 'Заказ', width: 90 },
    { key: 'Текст', label: 'Текст', width: 200 },
    { key: 'equipment_code', label: 'Код ЕО', width: 100 },
    { key: 'equipment_name', label: 'Наим. ЕО', width: 150 },
    { key: 'Вид', label: 'Вид', width: 120 },
    { key: 'STAT', label: 'Статус', width: 80 },
    { key: 'ABC', label: 'ABC', width: 50 },
    { key: 'Plan_N', label: 'План ₽', width: 90, align: 'right', fmt: fmtNum },
    { key: 'Fact_N', label: 'Факт ₽', width: 90, align: 'right', fmt: fmtNum },
    { key: 'Δ_Сумма', label: 'Δ ₽', width: 80, align: 'right', fmt: v => v > 0 ? `+${fmtShort(v)}` : fmtShort(v) },
    { key: 'Дата_Начало', label: 'Дата нач.', width: 90 },
    { key: 'Дата_Конец', label: 'Дата кон.', width: 90 },
    { key: 'Простой_Fmt', label: 'Простой', width: 100 },
    { key: 'Risk_Sum', label: 'Риск', width: 60, align: 'center' },
    { key: 'methods', label: 'Методы', width: 140 },
  ];

  const abcColors = {
    'Оч.высокая/Особокрит': 'maroon', 'Оч.высокая': 'maroon', 'Особокритичное': 'maroon',
    'A': 'danger', 'Высококритичное': 'danger', 'Высокая': 'danger',
    'B': 'orange', 'Средней критичности': 'orange', 'Средняя': 'orange', 'Средней крит.': 'orange',
    'Низкой критичности': 'warning',
    'C': 'accent', 'Не критично': 'accent',
    'Н/Д': 'muted',
  };

  const quickOpts = data?.quick_options || {};

  return (
    <div>
      <DateFootnote />
      <SectionTitle sub="Детализация сроков, отклонений и сработавших методов риска">
        Просмотр заказов
      </SectionTitle>

      <KpiRow>
        <KpiCard title="ВСЕГО" value={fmtNum(data.total)} />
        <KpiCard title="СТРАНИЦА" value={`${data.page} / ${data.pages}`} />
      </KpiRow>

      {/* Быстрые фильтры */}
      <Card title="Быстрые фильтры">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8, marginBottom: 8 }}>
          <TagSelect label="Автор (USER)" options={quickOpts.author || []} value={qf.author} onChange={v => updateQf('author', v)} placeholder="Выбрать автора..." />
          <TagSelect label="Тех. место (ТМ)" options={quickOpts.tm || []} value={qf.tm} onChange={v => updateQf('tm', v)} placeholder="Выбрать ТМ..." />
          <TagSelect label="Метод" options={quickOpts.method || []} value={qf.method} onChange={v => updateQf('method', v)} placeholder="Выбрать метод..." />
          <TagSelect label="Цех" options={quickOpts.ceh || []} value={qf.ceh} onChange={v => updateQf('ceh', v)} placeholder="Выбрать цех..." />
          <TagSelect label="Завод" options={quickOpts.zavod || []} value={qf.zavod} onChange={v => updateQf('zavod', v)} placeholder="Выбрать завод..." />
          <TagSelect label="Раб. место (РМ)" options={quickOpts.rm || []} value={qf.rm} onChange={v => updateQf('rm', v)} placeholder="Выбрать РМ..." />
          <TagSelect label="Оборудование (ЕО)" options={quickOpts.eo || []} value={qf.eo} onChange={v => updateQf('eo', v)} placeholder="Выбрать ЕО..." />
        </div>
        {/* Расширенный поиск по ЕО (название + код) */}
        <div style={{ marginBottom: 8, position: 'relative' }}>
          <label style={{ fontSize: 12, color: C.dim, display: 'block', marginBottom: 3 }}>Поиск оборудования (по названию или коду ЕО)</label>
          {/* Теги выбранных ЕО */}
          {eoTags.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
              {eoTags.map(tag => (
                <span key={tag.code} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 3,
                  padding: '2px 8px', borderRadius: 4, fontSize: 11,
                  background: `${C.accent}20`, color: C.accent, border: `1px solid ${C.accent}40`,
                }}>
                  <span style={{ fontWeight: 600 }}>{tag.code}</span>
                  {tag.name && <span style={{ color: C.muted, marginLeft: 2 }}>{tag.name.length > 30 ? tag.name.slice(0,30)+'...' : tag.name}</span>}
                  <button onClick={() => removeEoTag(tag.code)} style={{
                    background: 'none', border: 'none', color: C.accent, cursor: 'pointer', padding: 0, fontSize: 13, lineHeight: 1,
                  }}>×</button>
                </span>
              ))}
            </div>
          )}
          <input
            value={eoSearchQuery}
            onChange={e => setEoSearchQuery(e.target.value)}
            placeholder="Введите название или код ЕО..."
            style={{
              width: '100%', padding: '6px 10px', background: C.bg, border: `1px solid ${C.border}`,
              borderRadius: 6, color: C.text, fontSize: 12, outline: 'none', boxSizing: 'border-box',
            }}
          />
          {eoSearchLoading && <span style={{ fontSize: 11, color: C.muted, marginLeft: 6 }}>Поиск...</span>}
          {eoSearchResults.length > 0 && (
            <div style={{
              position: 'absolute', left: 0, right: 0, zIndex: 100,
              background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
              maxHeight: 220, overflowY: 'auto', marginTop: 2,
              boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
            }}>
              {eoSearchResults.map((item, idx) => (
                <div key={idx} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '6px 10px', fontSize: 12, color: C.text,
                  borderBottom: `1px solid ${C.border}33`,
                }}
                  onMouseEnter={e => e.currentTarget.style.background = `${C.accent}15`}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <span>
                    <span style={{ color: C.accent, fontWeight: 600 }}>{item.code}</span>
                    {item.name && <span style={{ color: C.muted, marginLeft: 6 }}>{item.name}</span>}
                  </span>
                  <button onClick={() => addEoTag(item)} style={{
                    padding: '2px 8px', background: `${C.accent}20`, border: `1px solid ${C.accent}40`,
                    borderRadius: 4, color: C.accent, cursor: 'pointer', fontSize: 14, lineHeight: 1, flexShrink: 0,
                  }}>+</button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Поиск по номерам заказов */}
        <div style={{ marginBottom: 8 }}>
          <label style={{ fontSize: 12, color: C.dim, display: 'block', marginBottom: 3 }}>Номера заказов (через запятую)</label>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              value={orderIdInput}
              onChange={e => setOrderIdInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') addOrderIds(); }}
              placeholder="000401, 000402, 000403..."
              style={{
                flex: 1, padding: '6px 10px', background: C.bg, border: `1px solid ${C.border}`,
                borderRadius: 6, color: C.text, fontSize: 12, outline: 'none',
              }}
            />
            <button onClick={addOrderIds} style={{
              padding: '6px 12px', background: C.surface, border: `1px solid ${C.border}`,
              borderRadius: 6, color: C.accent, cursor: 'pointer', fontSize: 12,
            }}>+</button>
          </div>
          {qf.order_ids.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
              {qf.order_ids.map(id => (
                <span key={id} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 3,
                  padding: '1px 6px', borderRadius: 4, fontSize: 11,
                  background: `${C.accent}20`, color: C.accent, border: `1px solid ${C.accent}40`,
                }}>
                  {id}
                  <button onClick={() => updateQf('order_ids', qf.order_ids.filter(x => x !== id))} style={{
                    background: 'none', border: 'none', color: C.accent, cursor: 'pointer', padding: 0, fontSize: 13,
                  }}>×</button>
                </span>
              ))}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={applyQuickFilters} style={{
            padding: '8px 20px', background: C.accent, border: 'none',
            borderRadius: 6, color: C.bg, cursor: 'pointer', fontSize: 13, fontWeight: 600,
          }}>Применить</button>
          <button onClick={resetQuickFilters} style={{
            padding: '8px 16px', background: C.surface, border: `1px solid ${C.border}`,
            borderRadius: 6, color: C.muted, cursor: 'pointer', fontSize: 12,
          }}>Сбросить</button>
          <div style={{ borderLeft: `1px solid ${C.border}`, height: 24, margin: '0 4px' }} />
          <button
            onClick={() => { setStarredActive(!starredActive); setPage(1); }}
            style={{
              padding: '8px 16px',
              background: starredActive ? `${C.warning}20` : C.surface,
              border: `1px solid ${starredActive ? C.warning : C.border}`,
              borderRadius: 6,
              color: starredActive ? C.warning : C.muted,
              cursor: totalStarred > 0 ? 'pointer' : 'not-allowed',
              fontSize: 13, fontWeight: starredActive ? 600 : 400,
              opacity: totalStarred > 0 ? 1 : 0.5,
            }}
            disabled={totalStarred === 0}
            title={totalStarred > 0 ? 'Показать только избранные заказы и ЕО' : 'Нет избранных элементов'}
          >
            ★ Избранное{totalStarred > 0 ? ` (${totalStarred})` : ''}
          </button>
          {totalStarred > 0 && (
            <button onClick={() => { clearAll(); setStarredActive(false); }} style={{
              padding: '8px 12px', background: C.surface, border: `1px solid ${C.border}`,
              borderRadius: 6, color: C.dim, cursor: 'pointer', fontSize: 11,
            }} title="Очистить все звёздочки">Очистить ★</button>
          )}
        </div>
      </Card>

      <Card>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                {columns.map(col => (
                  <th key={col.key}
                    onClick={() => handleSort(col.key)}
                    style={{
                      color: sort === col.key ? C.accent : C.muted,
                      fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap',
                      textAlign: col.align || 'left',
                      minWidth: col.width,
                    }}>
                    {col.label} {sort === col.key ? (order === 'desc' ? '▼' : '▲') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.data.map((row, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                  {columns.map(col => {
                    const val = row[col.key];
                    const display = col.fmt ? col.fmt(val) : (val ?? '—');

                    if (col.key === 'ID') {
                      return <td key={col.key} style={{ color: C.accent, fontSize: 13, fontWeight: 600 }}>
                        <StarButton active={isOrderStarred(val)} onClick={() => toggleOrder(val)} size={12} />{' '}{display}
                      </td>;
                    }
                    if (col.key === 'ABC') {
                      return <td key={col.key}><Badge variant={abcColors[val] || 'muted'}>{val || '—'}</Badge></td>;
                    }
                    if (col.key === 'Risk_Sum') {
                      const clr = val > 4 ? C.danger : val > 2 ? C.warning : val > 0 ? C.orange : C.dim;
                      return <td key={col.key} style={{ textAlign: 'center', color: clr, fontWeight: 700 }}>{val || 0}</td>;
                    }
                    if (col.key === 'methods') {
                      return (
                        <td key={col.key} style={{ fontSize: 11 }}>
                          {val ? val.split(', ').map(m => <Badge key={m} variant="muted">{m}</Badge>) : '—'}
                        </td>
                      );
                    }
                    if (col.key === 'Δ_Сумма') {
                      const clr = val > 0 ? C.danger : val < 0 ? C.success : C.muted;
                      return <td key={col.key} style={{ textAlign: 'right', color: clr, fontSize: 13 }}>{display}</td>;
                    }
                    if (col.key === 'equipment_name') {
                      return (
                        <td key={col.key} style={{
                          color: C.text, fontSize: 12, maxWidth: col.width,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }} title={String(val || '')}>
                          {val && <><StarButton active={isEOStarred(val)} onClick={() => toggleEO(val)} size={11} />{' '}</>}
                          {display}
                        </td>
                      );
                    }
                    if (col.key === 'Дата_Начало' || col.key === 'Дата_Конец') {
                      const src = row['Источник_Дат'];
                      const clr = src === 'FACT' ? C.success : src === 'NOTIFY' ? C.accent : src === 'PLAN' ? C.warning : C.danger;
                      const mark = src === 'PLAN' ? ' \u2022' : src === 'NOTIFY' ? ' \u25cb' : '';
                      const txt = val ? val + mark : '\u2014';
                      return <td key={col.key} style={{ color: clr, fontSize: 12 }}>{txt}</td>;
                    }
                    if (col.key === 'Простой_Fmt') {
                      const dtVal = val && val !== '0' ? val : '\u2014';
                      const dtClr = val && val !== '0' ? C.accent : C.dim;
                      return <td key={col.key} style={{ color: dtClr, fontSize: 12 }}>{dtVal}</td>;
                    }

                    return (
                      <td key={col.key} style={{
                        color: C.text, fontSize: 12,
                        textAlign: col.align || 'left',
                        maxWidth: col.width, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }} title={String(val || '')}>
                        {display}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Пагинация */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1}
            style={{ padding: '6px 16px', background: C.surface, border: `1px solid ${C.border}`,
              borderRadius: 6, color: page <= 1 ? C.dim : C.accent, cursor: 'pointer' }}>
            ← Назад
          </button>
          <span style={{ color: C.muted, padding: '6px 12px', fontSize: 13 }}>
            {data.page} / {data.pages}
          </span>
          <button onClick={() => setPage(Math.min(data.pages, page + 1))} disabled={page >= data.pages}
            style={{ padding: '6px 16px', background: C.surface, border: `1px solid ${C.border}`,
              borderRadius: 6, color: page >= data.pages ? C.dim : C.accent, cursor: 'pointer' }}>
            Вперёд →
          </button>
        </div>
      </Card>

      {/* Экспорт */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
        <button onClick={() => apiDownload('/api/export/excel', { session_id: sessionId, filters: buildFilters(), debouncedThresholds })}
          style={{
            padding: '10px 20px', background: C.surface, border: `1px solid ${C.accent}`,
            borderRadius: 8, color: C.accent, cursor: 'pointer', fontSize: 13,
          }}>
          Выгрузить в Excel
        </button>
      </div>
    </div>
  );
}
