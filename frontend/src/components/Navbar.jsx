import { C, GRADIENTS } from '../theme/arctic';

export default function Navbar({ fileInfo }) {
  return (
    <nav style={{
      background: GRADIENTS.navbar,
      borderBottom: `2px solid ${C.accent}`,
      padding: '14px 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 50,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 24, fontWeight: 700, color: C.accent }}>ТИТАН</span>
        <span style={{ fontSize: 14, color: C.muted }}>Аудит ТОРО v.200</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 12, color: C.dim }}>
        {fileInfo && (
          <span style={{ color: C.muted }}>
            {fileInfo.name} | {fileInfo.rows} строк | {fileInfo.time}
          </span>
        )}
        <span>ARCTIC DARK</span>
      </div>
    </nav>
  );
}
