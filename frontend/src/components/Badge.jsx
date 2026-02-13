import { C } from '../theme/arctic';

const PRESETS = {
  danger: { bg: 'rgba(244,63,94,0.15)', color: C.danger, border: C.danger },
  warning: { bg: 'rgba(251,191,36,0.15)', color: C.warning, border: C.warning },
  success: { bg: 'rgba(52,211,153,0.15)', color: C.success, border: C.success },
  accent: { bg: 'rgba(56,189,248,0.15)', color: C.accent, border: C.accent },
  purple: { bg: 'rgba(167,139,250,0.15)', color: C.purple, border: C.purple },
  muted: { bg: 'rgba(100,116,139,0.15)', color: C.muted, border: C.dim },
};

/**
 * Бейдж/тег
 */
export default function Badge({ children, variant = 'accent' }) {
  const s = PRESETS[variant] || PRESETS.accent;
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 600,
      background: s.bg,
      color: s.color,
      border: `1px solid ${s.border}44`,
    }}>
      {children}
    </span>
  );
}
