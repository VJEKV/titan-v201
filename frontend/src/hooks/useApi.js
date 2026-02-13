import { useState, useCallback } from 'react';
import { apiGet } from '../api/client';

/**
 * Хук для запросов с loading/error состояниями
 */
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const request = useCallback(async (endpoint, params = {}) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet(endpoint, params);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, request };
}
