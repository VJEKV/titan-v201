import { C } from '../theme/arctic';

/**
 * DateFootnote — сноска-легенда источника дат.
 * Размещается НАД компонентами с датами.
 */
export default function DateFootnote() {
  return (
    <div style={{ fontSize: 11, marginBottom: 8, color: C.muted }}>
      <span style={{ color: C.cyan }}>Даты: </span>
      <span style={{ color: '#ffffff' }}>белый</span> — фактическая,{' '}
      <span style={{ color: C.warning }}>жёлтый •</span> — плановая,{' '}
      <span style={{ color: C.danger }}>красный</span> — отсутствует
    </div>
  );
}
