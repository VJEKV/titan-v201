import { useState, useRef, useEffect } from 'react';
import { C } from '../theme/arctic';

/**
 * Мультиселект с тегами (chips) и поиском
 * @param {string} label — Заголовок
 * @param {string[]} options — Доступные значения
 * @param {string[]} value — Выбранные значения
 * @param {Function} onChange — Колбэк (newValues)
 * @param {string} placeholder — Подсказка
 */
export default function TagSelect({ label, options = [], value = [], onChange, placeholder = 'Поиск...' }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef(null);

  // Закрытие по клику вне компонента
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filtered = options.filter(o =>
    !value.includes(o) && o.toLowerCase().includes(search.toLowerCase())
  );

  const addTag = (v) => {
    onChange([...value, v]);
    setSearch('');
  };

  const removeTag = (v) => {
    onChange(value.filter(x => x !== v));
  };

  return (
    <div ref={ref} style={{ marginBottom: 10, position: 'relative' }}>
      {label && (
        <label style={{ fontSize: 12, color: C.dim, display: 'block', marginBottom: 3 }}>{label}</label>
      )}

      {/* Теги */}
      <div
        onClick={() => setOpen(true)}
        style={{
          display: 'flex', flexWrap: 'wrap', gap: 4, padding: '4px 6px',
          background: C.bg, border: `1px solid ${open ? C.accent : C.border}`,
          borderRadius: 6, minHeight: 32, cursor: 'text', alignItems: 'center',
          transition: 'border-color 0.15s',
        }}
      >
        {value.map(v => (
          <span key={v} style={{
            display: 'inline-flex', alignItems: 'center', gap: 3,
            padding: '1px 6px', borderRadius: 4, fontSize: 11,
            background: `${C.accent}20`, color: C.accent, border: `1px solid ${C.accent}40`,
            whiteSpace: 'nowrap', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{v}</span>
            <button
              onClick={(e) => { e.stopPropagation(); removeTag(v); }}
              style={{
                background: 'none', border: 'none', color: C.accent, cursor: 'pointer',
                padding: 0, fontSize: 13, lineHeight: 1, flexShrink: 0,
              }}
            >
              ×
            </button>
          </span>
        ))}
        <input
          value={search}
          onChange={e => { setSearch(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder={value.length === 0 ? placeholder : ''}
          style={{
            background: 'none', border: 'none', outline: 'none', color: C.text,
            fontSize: 12, flex: 1, minWidth: 50, padding: '2px 0',
          }}
        />
      </div>

      {/* Выпадающий список */}
      {open && filtered.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
          background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
          maxHeight: 200, overflowY: 'auto', marginTop: 2,
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        }}>
          {filtered.slice(0, 50).map(o => (
            <div
              key={o}
              onClick={() => addTag(o)}
              style={{
                padding: '6px 10px', cursor: 'pointer', fontSize: 12, color: C.text,
                borderBottom: `1px solid ${C.border}33`,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
              onMouseEnter={e => e.currentTarget.style.background = `${C.accent}15`}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              {o}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
