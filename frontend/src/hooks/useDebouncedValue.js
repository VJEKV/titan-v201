import { useEffect, useState } from 'react';

/**
 * useDebouncedValue — возвращает значение с задержкой `delay` мс.
 * Используется чтобы не дёргать API на каждое нажатие клавиши /
 * каждый клик в фильтре. Изменения, идущие чаще `delay`, схлопываются
 * в одно — последнее значение применяется только когда поток ввода
 * остановился на `delay` мс.
 *
 * Пример:
 *   const debouncedFilters = useDebouncedValue(filters, 300);
 *   useEffect(() => fetchData(debouncedFilters), [debouncedFilters]);
 *
 * ТИТАН-5.
 */
export function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

export default useDebouncedValue;
