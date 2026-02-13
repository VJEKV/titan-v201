import { useState, useEffect, useCallback } from 'react';
import { C, METHOD_COLORS } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';
import { apiGet } from '../api/client';
import KpiCard from '../components/KpiCard';
import KpiRow from '../components/KpiRow';
import SectionTitle from '../components/SectionTitle';
import MethodCard from '../components/MethodCard';
import ProgressBar from '../components/ProgressBar';
import Badge from '../components/Badge';
import Card from '../components/Card';

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

/** Описания методов для аудиторов */
const METHOD_DETAILS = {
  "C1-M1": {
    title: "Перерасход бюджета",
    logic: "Сравнение фактических затрат с плановыми. Если (Факт/План - 1) × 100% превышает порог — фиксируется аномалия.",
    risks: "Необоснованное завышение объёмов работ, ошибки в планировании, несанкционированные дополнительные работы.",
    audit: "Проверить обоснование перерасхода, наличие дополнительных соглашений, корректность списания материалов."
  },
  "C1-M6": {
    title: "Аномалия по истории ТМ",
    logic: "Фактическая стоимость заказа сравнивается с медианой по техническому месту. Если Факт > Медиана × (Порог/100) — аномалия.",
    risks: "Завышение стоимости работ на конкретном оборудовании, дублирование затрат, некорректная привязка к ТМ.",
    audit: "Сравнить с аналогичными заказами на том же ТМ, проверить состав работ и материалов."
  },
  "C1-M9": {
    title: "Незавершённые работы",
    logic: "Статус заказа содержит ОТКР, «В работе» или «Внутреннее планирование» — заказ не закрыт.",
    risks: "Зависшие заказы, неконтролируемое накопление затрат, отсутствие приёмки работ.",
    audit: "Выяснить причину незакрытия, проверить фактическое выполнение работ, инициировать закрытие."
  },
  "C2-M2": {
    title: "Проблемное оборудование",
    logic: "Подсчёт количества заказов на единицу оборудования (ЕО). Если количество > Порога — оборудование проблемное. Заказы без ЕО не учитываются.",
    risks: "Систематические поломки, неэффективный ремонт, необходимость замены оборудования.",
    audit: "Оценить историю ремонтов ЕО, сравнить затраты с остаточной стоимостью, рассмотреть замену."
  },
  "NEW-9": {
    title: "Формальное закрытие в декабре",
    logic: "Заказ закрыт в декабре (Факт_Конец), хотя плановое окончание не в декабре, и фактическая длительность подозрительно мала.",
    risks: "Формальное закрытие для списания бюджета в конце года, работы фактически не завершены.",
    audit: "Проверить акты выполненных работ, физическое завершение, корректность дат."
  },
  "NEW-10": {
    title: "Возвраты статусов",
    logic: "Подсчёт количества откатов статуса заказа на предыдущий. Если возвратов > Порога — аномалия.",
    risks: "Манипуляции с документооборотом, исправление ошибок задним числом, несогласованность процессов.",
    audit: "Изучить историю статусов, выявить причины возвратов, проверить корректность согласований."
  }
};

/** Сворачиваемый блок методологии */
function MethodologyBlock() {
  const LS_KEY = 'risks_methodology_expanded';
  const [expanded, setExpanded] = useState(() => {
    try { return localStorage.getItem(LS_KEY) === 'true'; } catch { return false; }
  });

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    try { localStorage.setItem(LS_KEY, String(next)); } catch {}
  };

  return (
    <div style={{
      background: 'linear-gradient(145deg, #1e293b 0%, #273548 100%)',
      borderRadius: 10, border: `1px solid ${C.border}`,
      padding: 20, marginBottom: 16,
    }}>
      <h3 onClick={toggle} style={{
        fontSize: 16, fontWeight: 600, color: C.accent, marginBottom: expanded ? 14 : 0,
        cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none',
      }}>
        <span style={{
          display: 'inline-block', transition: 'transform 0.2s',
          transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
          fontSize: 12,
        }}>&#9654;</span>
        Методология расчёта приоритетов
      </h3>
      <div style={{
        maxHeight: expanded ? 1000 : 0,
        overflow: 'hidden',
        transition: 'max-height 0.35s ease',
        opacity: expanded ? 1 : 0,
      }}>
        <div style={{ color: C.text, fontSize: 13, lineHeight: 1.7 }}>
          <p style={{ marginBottom: 8 }}>
            <strong style={{ color: C.accent }}>Приоритет</strong> = Сумма методов × Множитель + Качество данных × 0.8
          </p>
          <p style={{ marginBottom: 8, color: C.muted }}>
            <strong>Сумма методов</strong> — взвешенная сумма баллов по 6 методам (каждый метод 0-10 баллов × вес).
          </p>
          <p style={{ marginBottom: 8, color: C.muted }}>
            <strong>Множитель</strong> — коэффициент по количеству сработавших методов: 1→1.0, 2→1.3, 3→1.7, 4→2.2, 5→2.5, 6→3.0.
          </p>
          <p style={{ marginBottom: 8, color: C.muted }}>
            <strong>Качество данных</strong> = 10 × (1 − Полнота/100) — штраф за некачественные данные.
          </p>
          <p style={{ marginBottom: 12, color: C.muted }}>
            <strong>Линейный скоринг:</strong> значение = порогу → 5 баллов, 2×порог → 10 баллов, ниже порога → пропорционально.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
            <div style={{ padding: '8px 12px', borderRadius: 6, background: `${C.danger}12`, borderLeft: `4px solid ${C.danger}` }}>
              <strong style={{ color: C.danger }}>Красный (Приоритет &gt; 7)</strong>
              <div style={{ color: C.muted, fontSize: 12 }}>Критичный риск. Высокий балл методов при хорошем качестве данных — явные нарушения, требующие немедленной проверки.</div>
            </div>
            <div style={{ padding: '8px 12px', borderRadius: 6, background: `${C.warning}12`, borderLeft: `4px solid ${C.warning}` }}>
              <strong style={{ color: C.warning }}>Жёлтый (Приоритет 4-7)</strong>
              <div style={{ color: C.muted, fontSize: 12 }}>Повышенный риск. Средний балл методов и/или плохое качество данных — подозрительные заказы для детальной проверки.</div>
            </div>
            <div style={{ padding: '8px 12px', borderRadius: 6, background: `${C.dim}12`, borderLeft: `4px solid ${C.dim}` }}>
              <strong style={{ color: C.dim }}>Серый (Приоритет 1-4)</strong>
              <div style={{ color: C.muted, fontSize: 12 }}>Умеренный риск. Низкий балл методов, но высокий штраф за качество данных — непроверяемые из-за нехватки информации.</div>
            </div>
            <div style={{ padding: '8px 12px', borderRadius: 6, background: `${C.success}12`, borderLeft: `4px solid ${C.success}` }}>
              <strong style={{ color: C.success }}>Зелёный (Приоритет &lt; 1)</strong>
              <div style={{ color: C.muted, fontSize: 12 }}>Норма. Методы не сработали, данные полные — чистые заказы без выявленных аномалий.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Risks({ setActiveMethod, setActiveTab }) {
  const { sessionId, filters, thresholds } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);

  const loadData = useCallback(() => {
    if (!sessionId) return;
    setLoading(true);
    apiGet('/api/tab/risks', { session_id: sessionId, filters, thresholds, page, page_size: pageSize })
      .then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId, filters, thresholds, page, pageSize]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { setPage(1); }, [filters, thresholds]);

  if (loading && !data) return <p style={{ color: C.muted }}>Загрузка...</p>;
  if (!data) return null;

  const { kpi, methods, top_priority, categories, pages: totalPages, total_orders } = data;

  const CATEGORY_COLORS = {
    'Красный': C.danger,
    'Жёлтый': C.warning,
    'Серый': C.dim,
    'Зелёный': C.success,
  };

  return (
    <div>
      <SectionTitle sub="6 аналитических методов — непрерывный скоринг v2 (шкала 0-10)">
        Риск-скоринг: Приоритеты аудита
      </SectionTitle>

      <KpiRow>
        <KpiCard title="ВСЕГО ЗАКАЗОВ" value={fmtNum(kpi.total)} />
        <KpiCard title="С РИСКОМ (>0)" value={fmtNum(kpi.risk_count)} sub={`${kpi.risk_pct}%`} color={C.danger} />
        <KpiCard title="СУММА ПРИОРИТЕТОВ" value={kpi.risk_sum_total} />
        <KpiCard title="СРЕДНИЙ БАЛЛ" value={kpi.avg_score} />
      </KpiRow>

      {/* Категории */}
      {categories && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          {[
            { key: 'red', label: 'Красные (>7)', color: C.danger, count: categories.red },
            { key: 'yellow', label: 'Жёлтые (4-7)', color: C.warning, count: categories.yellow },
            { key: 'grey', label: 'Серые (1-4)', color: C.dim, count: categories.grey },
            { key: 'green', label: 'Зелёные (<1)', color: C.success, count: categories.green },
          ].map(cat => (
            <div key={cat.key} style={{
              padding: '8px 16px', borderRadius: 8, flex: '1 1 120px',
              background: `${cat.color}15`, borderLeft: `4px solid ${cat.color}`,
            }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: cat.color }}>{fmtNum(cat.count)}</div>
              <div style={{ fontSize: 11, color: C.muted }}>{cat.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Методы с описаниями — единый размер карточек */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: 12, marginBottom: 20 }}>
        {methods.map(m => {
          const methodKey = m.name.split(':')[0];
          const details = METHOD_DETAILS[methodKey];
          return (
            <div key={m.name} style={{ display: 'flex', flexDirection: 'column' }}>
              <div onClick={() => {
                const shortName = m.name.split(':')[0];
                if (setActiveMethod) setActiveMethod(shortName);
                if (setActiveTab) setActiveTab('orders');
              }} style={{ cursor: 'pointer' }}>
                <MethodCard name={m.name} desc={m.desc} count={m.count}
                  total={m.total} sum={m.sum} color={m.color} threshold={m.threshold} icon={m.icon}
                  orders_without_eo={m.orders_without_eo} />
              </div>
              {details && (
                <div style={{
                  marginTop: -6, flex: 1, padding: '10px 16px',
                  background: `${C.surface}`, borderRadius: '0 0 10px 10px',
                  borderLeft: `5px solid ${m.color || C.accent}`,
                  border: `1px solid ${C.border}`, borderTop: 'none',
                  fontSize: 12, lineHeight: 1.6,
                }}>
                  <div style={{ color: C.muted, marginBottom: 4 }}>
                    <strong style={{ color: C.text }}>Логика:</strong> {details.logic}
                  </div>
                  <div style={{ color: C.muted, marginBottom: 4 }}>
                    <strong style={{ color: C.danger }}>Риски:</strong> {details.risks}
                  </div>
                  <div style={{ color: C.muted }}>
                    <strong style={{ color: C.success }}>Аудитору:</strong> {details.audit}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Описание Risk Scoring v2 — сворачиваемый блок */}
      <MethodologyBlock />

      {/* Таблица заказов с пагинацией */}
      {top_priority.length > 0 && (
        <Card title={`Приоритетные заказы — ${total_orders || '?'} заказов`}>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr style={{ background: C.bg, borderBottom: `2px solid ${C.border}` }}>
                  {['#', 'ID', 'Текст', 'ТМ', 'ЕО', 'Наименование оборуд.', 'Вид', 'План', 'Факт', 'Приоритет', 'Кач. данных', 'Категория', 'Методы', 'Полнота'].map(h => (
                    <th key={h} style={{ color: C.muted, fontSize: 11, whiteSpace: 'nowrap', padding: '8px 6px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {top_priority.map((r, i) => {
                  const catColor = CATEGORY_COLORS[r.category] || C.dim;
                  const rowNum = (page - 1) * pageSize + i + 1;
                  return (
                    <tr key={i} style={{ borderBottom: `1px solid ${C.border}33` }}>
                      <td style={{ color: C.dim, fontSize: 12, padding: '6px' }}>{rowNum}</td>
                      <td style={{ color: C.accent, fontSize: 13, fontWeight: 600, padding: '6px' }}>{r.id}</td>
                      <td style={{ color: C.text, fontSize: 12, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px' }}
                        title={r.text}>{r.text}</td>
                      <td style={{ color: C.muted, fontSize: 12, maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px' }}
                        title={r.tm}>{r.tm}</td>
                      <td style={{ color: C.muted, fontSize: 12, maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px' }}
                        title={r.eo || ''}>{r.eo || '—'}</td>
                      <td style={{ color: C.muted, fontSize: 12, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '6px' }}
                        title={r.eo_name || ''}>{r.eo_name || '—'}</td>
                      <td style={{ color: C.muted, fontSize: 12, padding: '6px' }}>{r.vid}</td>
                      <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px' }}>{fmtShort(r.plan)}</td>
                      <td style={{ color: C.text, fontSize: 12, textAlign: 'right', padding: '6px' }}>{fmtShort(r.fact)}</td>
                      <td style={{ textAlign: 'center', minWidth: 100, padding: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <ProgressBar value={r.risk_sum || 0} max={10} />
                          <span style={{ color: C.text, fontSize: 12, fontWeight: 600, minWidth: 28 }}>
                            {(r.priority_score || r.risk_sum || 0).toFixed(1)}
                          </span>
                        </div>
                      </td>
                      <td style={{ color: C.warning, fontSize: 12, textAlign: 'center', padding: '6px' }}>
                        {(r.dq_risk || 0).toFixed(1)}
                      </td>
                      <td style={{ textAlign: 'center', padding: '6px' }}>
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 11,
                          fontWeight: 600, color: catColor, background: `${catColor}15`,
                          border: `1px solid ${catColor}40`,
                        }}>
                          {r.category || '—'}
                        </span>
                      </td>
                      <td style={{ fontSize: 11, padding: '6px' }}>
                        {r.methods.map(m => {
                          const clr = METHOD_COLORS[m] || C.muted;
                          return <Badge key={m} variant="muted"><span style={{ color: clr }}>{m}</span></Badge>;
                        })}
                      </td>
                      <td style={{ color: C.muted, fontSize: 12, textAlign: 'center', padding: '6px' }}>{r.completeness}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Пагинация */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 16 }}>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                style={{
                  padding: '6px 14px', background: page <= 1 ? C.bg : C.surface,
                  border: `1px solid ${C.border}`, borderRadius: 6,
                  color: page <= 1 ? C.dim : C.accent, cursor: page <= 1 ? 'default' : 'pointer', fontSize: 12,
                }}
              >
                Назад
              </button>
              <span style={{ color: C.muted, fontSize: 13 }}>
                Стр. <strong style={{ color: C.text }}>{page}</strong> из <strong style={{ color: C.text }}>{totalPages}</strong>
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                style={{
                  padding: '6px 14px', background: page >= totalPages ? C.bg : C.surface,
                  border: `1px solid ${C.border}`, borderRadius: 6,
                  color: page >= totalPages ? C.dim : C.accent, cursor: page >= totalPages ? 'default' : 'pointer', fontSize: 12,
                }}
              >
                Вперёд
              </button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
