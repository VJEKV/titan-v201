import { C } from '../theme/arctic';

/**
 * Прогресс-бар
 */
export default function ProgressBar({ value, max = 10, color, height = 6 }) {
  const pct = Math.min((value / max) * 100, 100);
  const clr = color || (pct > 70 ? C.danger : pct > 40 ? C.warning : C.success);

  return (
    <div style={{
      background: C.border,
      borderRadius: height / 2,
      height,
      width: '100%',
      overflow: 'hidden',
    }}>
      <div style={{
        background: clr,
        height: '100%',
        width: `${pct}%`,
        borderRadius: height / 2,
        transition: 'width 0.3s ease',
      }} />
    </div>
  );
}
