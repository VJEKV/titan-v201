import { C } from '../theme/arctic';

/**
 * Кнопка-звёздочка для избранного.
 * ★ (заполненная) когда active, ☆ (пустая) когда нет.
 */
export default function StarButton({ active, onClick, size = 14 }) {
  return (
    <span
      onClick={e => { e.stopPropagation(); onClick && onClick(); }}
      style={{
        cursor: 'pointer',
        fontSize: size,
        color: active ? C.warning : C.dim,
        lineHeight: 1,
        userSelect: 'none',
        transition: 'color 0.15s',
        display: 'inline-flex',
        alignItems: 'center',
      }}
      title={active ? 'Убрать из избранного' : 'Добавить в избранное'}
    >
      {active ? '★' : '☆'}
    </span>
  );
}
