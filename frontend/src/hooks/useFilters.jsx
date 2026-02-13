import React, { createContext, useContext, useState } from 'react';

const FiltersContext = createContext(null);

const DEFAULT_FILTERS = {
  hierarchy: {
    'БЕ': [], 'ЗАВОД': [], 'ПРОИЗВОДСТВО': [],
    'ЦЕХ': [], 'УСТАНОВКА': [], 'ЕО': []
  },
  search: '',
  vid: [],
  abc: [],
  stat: [],
  rm: [],
  ingrp: [],
  date_from: '',
  date_to: '',
};

const DEFAULT_THRESHOLDS = {
  "C1-M1: Перерасход бюджета": 20,
  "C1-M6: Аномалия по истории ТМ": 140,
  "C1-M9: Незавершённые работы": 0,
  "C2-M2: Проблемное оборудование": 5,
  "NEW-9: Формальное закрытие в декабре": 50,
  "NEW-10: Возвраты статусов": 3,
};

export function FiltersProvider({ children }) {
  const [sessionId, setSessionId] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS);
  const [fileInfo, setFileInfo] = useState(null);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const updateHierarchy = (level, values) => {
    setFilters(prev => ({
      ...prev,
      hierarchy: { ...prev.hierarchy, [level]: values }
    }));
  };

  const updateThreshold = (method, value) => {
    setThresholds(prev => ({ ...prev, [method]: value }));
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  return (
    <FiltersContext.Provider value={{
      sessionId, setSessionId,
      filters, setFilters, updateFilter, updateHierarchy, resetFilters,
      thresholds, updateThreshold,
      fileInfo, setFileInfo,
    }}>
      {children}
    </FiltersContext.Provider>
  );
}

export function useFilters() {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error('useFilters must be used within FiltersProvider');
  return ctx;
}
