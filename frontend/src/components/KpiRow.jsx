/**
 * Ряд KPI карточек
 */
export default function KpiRow({ children }) {
  return (
    <div style={{
      display: 'flex',
      gap: 12,
      flexWrap: 'wrap',
      marginBottom: 20,
    }}>
      {children}
    </div>
  );
}
