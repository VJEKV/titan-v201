import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const StarredContext = createContext(null);
const LS_KEY = 'titan_starred_items';

/** Загрузка из localStorage */
function loadStarred() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return { orders: [], eo: [] };
    const parsed = JSON.parse(raw);
    return {
      orders: Array.isArray(parsed.orders) ? parsed.orders : [],
      eo: Array.isArray(parsed.eo) ? parsed.eo : [],
    };
  } catch { return { orders: [], eo: [] }; }
}

/** Сохранение в localStorage */
function saveStarred(orders, eo) {
  localStorage.setItem(LS_KEY, JSON.stringify({ orders, eo }));
}

export function StarredProvider({ children }) {
  const [starredOrders, setStarredOrders] = useState(() => new Set(loadStarred().orders));
  const [starredEO, setStarredEO] = useState(() => new Set(loadStarred().eo));

  // Персистентность
  useEffect(() => {
    saveStarred([...starredOrders], [...starredEO]);
  }, [starredOrders, starredEO]);

  const toggleOrder = useCallback((id) => {
    setStarredOrders(prev => {
      const next = new Set(prev);
      const key = String(id);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }, []);

  const toggleEO = useCallback((name) => {
    setStarredEO(prev => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }, []);

  const isOrderStarred = useCallback((id) => starredOrders.has(String(id)), [starredOrders]);
  const isEOStarred = useCallback((name) => starredEO.has(name), [starredEO]);

  const clearAll = useCallback(() => {
    setStarredOrders(new Set());
    setStarredEO(new Set());
  }, []);

  const totalStarred = starredOrders.size + starredEO.size;

  return (
    <StarredContext.Provider value={{
      starredOrders, starredEO,
      toggleOrder, toggleEO,
      isOrderStarred, isEOStarred,
      clearAll, totalStarred,
    }}>
      {children}
    </StarredContext.Provider>
  );
}

export function useStarred() {
  const ctx = useContext(StarredContext);
  if (!ctx) throw new Error('useStarred must be used within StarredProvider');
  return ctx;
}
