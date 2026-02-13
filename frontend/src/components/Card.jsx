import { C, GRADIENTS } from '../theme/arctic';

/**
 * Обёртка-карточка с градиентом
 */
export default function Card({ children, title, borderColor, style }) {
  return (
    <div style={{
      background: GRADIENTS.card,
      borderRadius: 10,
      border: `1px solid ${C.border}`,
      borderTop: borderColor ? `3px solid ${borderColor}` : undefined,
      padding: 20,
      marginBottom: 16,
      ...style,
    }}>
      {title && (
        <h3 style={{ fontSize: 16, fontWeight: 600, color: C.accent, marginBottom: 14 }}>
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}
