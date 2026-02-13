import { C } from '../theme/arctic';

/**
 * Заголовок секции
 */
export default function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 16, marginTop: 8 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, color: C.text }}>
        {children}
      </h2>
      {sub && (
        <p style={{ fontSize: 13, color: C.muted, marginTop: 4 }}>{sub}</p>
      )}
    </div>
  );
}
