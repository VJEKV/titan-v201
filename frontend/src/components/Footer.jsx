import { C } from '../theme/arctic';

export default function Footer() {
  return (
    <footer style={{
      textAlign: 'center',
      padding: '16px',
      color: C.dim,
      fontSize: 12,
      borderTop: `1px solid ${C.border}`,
      marginTop: 32,
    }}>
      ТИТАН Аудит ТОРО v.200 | ПВКА-01.2.04.8 | React + FastAPI
    </footer>
  );
}
