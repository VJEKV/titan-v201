import { useState } from 'react';
import { FiltersProvider, useFilters } from './hooks/useFilters';
import { C } from './theme/arctic';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import TabBar from './components/TabBar';
import Footer from './components/Footer';
import UploadScreen from './components/UploadScreen';
import KpiRow from './components/KpiRow';
import KpiCard from './components/KpiCard';
import { apiGet } from './api/client';
import { useEffect } from 'react';

// Вкладки
import Finance from './tabs/Finance';
import Timeline from './tabs/Timeline';
import WorkTypes from './tabs/WorkTypes';
import Planners from './tabs/Planners';
import Workplaces from './tabs/Workplaces';
import Risks from './tabs/Risks';
import Quality from './tabs/Quality';
import Equipment from './tabs/Equipment';
import Orders from './tabs/Orders';
import ChatWidget from './components/ChatWidget';

/** Форматирование числа с пробелами разрядов */
function fmtNum(v) {
  if (!v && v !== 0) return '0';
  return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

/** Короткий формат: 1.2М, 345К, 1.1Млрд */
function fmtShort(v) {
  if (!v && v !== 0) return '0';
  const a = Math.abs(v), s = v >= 0 ? '' : '-';
  if (a >= 1e9) return `${s}${(a / 1e9).toFixed(1)}Млрд`;
  if (a >= 1e6) return `${s}${(a / 1e6).toFixed(1)}М`;
  if (a >= 1e3) return `${s}${(a / 1e3).toFixed(1)}К`;
  return `${s}${a.toFixed(0)}`;
}

const TAB_COMPONENTS = {
  'finance': Finance,
  'timeline': Timeline,
  'work-types': WorkTypes,
  'planners': Planners,
  'workplaces': Workplaces,
  'risks': Risks,
  'quality': Quality,
  'equipment': Equipment,
  'orders': Orders,
};

/**
 * Основное содержимое приложения (внутри FiltersProvider)
 */
function AppContent() {
  const { sessionId, fileInfo, filters, thresholds } = useFilters();
  const [activeTab, setActiveTab] = useState('finance');
  const [activeMethod, setActiveMethod] = useState(null);
  const [kpi, setKpi] = useState(null);

  // Сброс старых кешированных палитр ice при первом запуске v200
  useEffect(() => {
    if (!localStorage.getItem('titan_version_200')) {
      Object.keys(localStorage).forEach(k => {
        if (k.startsWith('titan_chart_')) localStorage.removeItem(k);
      });
      localStorage.setItem('titan_version_200', 'true');
    }
  }, []);

  // Загрузка KPI при изменении фильтров
  useEffect(() => {
    if (!sessionId) return;
    apiGet('/api/kpi', { session_id: sessionId, filters, thresholds })
      .then(setKpi)
      .catch(() => {});
  }, [sessionId, filters, thresholds]);

  // Экран загрузки файла
  if (!sessionId) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: C.bg, color: C.text }}>
        <Navbar />
        <UploadScreen />
        <Footer />
      </div>
    );
  }

  const TabComponent = TAB_COMPONENTS[activeTab];

  return (
    <div style={{ minHeight: '100vh', backgroundColor: C.bg, color: C.text, display: 'flex', flexDirection: 'column' }}>
      <Navbar fileInfo={fileInfo} />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar />
        <main style={{ flex: 1, padding: '16px 24px', overflowX: 'hidden' }}>
          {/* KPI — основные показатели */}
          {kpi && (
            <>
              <KpiRow>
                <KpiCard title="ЗАКАЗОВ" value={fmtNum(kpi.total)} />
                <KpiCard title="ПЛАН (Σ)" value={`${kpi.plan_fmt || fmtShort(kpi.plan)} \u20BD`} />
                <KpiCard title="ФАКТ (Σ)" value={`${kpi.fact_fmt || fmtShort(kpi.fact)} \u20BD`} />
                <KpiCard title="ОТКЛОНЕНИЕ" value={`${kpi.dev_fmt || fmtShort(Math.abs(kpi.dev))} \u20BD`} sub={`${kpi.dev_pct > 0 ? '+' : ''}${kpi.dev_pct}%`} color={kpi.dev > 0 ? C.danger : C.success} />
                <KpiCard title="С РИСКОМ" value={fmtNum(kpi.risk_count)} sub={`${kpi.risk_pct}%`} color={C.warning} />
                <KpiCard title="ПОЛНОТА" value={`${kpi.completeness}%`} color={C.accent} />
              </KpiRow>
              {/* KPI — статистика по выгрузке */}
              {kpi.stats && (
                <KpiRow>
                  <KpiCard title="ЗАВОДОВ" value={fmtNum(kpi.stats.n_zavod)} icon="🏭" color={C.muted} />
                  <KpiCard title="ЕД. ОБОРУДОВАНИЯ" value={fmtNum(kpi.stats.n_eo)} icon="🔧" color={C.muted} />
                  <KpiCard title="ЦЕХОВ" value={fmtNum(kpi.stats.n_ceh)} icon="⚙️" color={C.muted} />
                  <KpiCard title="ТЕХ. МЕСТ" value={fmtNum(kpi.stats.n_tm)} icon="📍" color={C.muted} />
                  <KpiCard title="ПОЛЬЗОВАТЕЛЕЙ" value={fmtNum(kpi.stats.n_users)} icon="👤" color={C.muted} />
                </KpiRow>
              )}
            </>
          )}

          {/* Вкладки */}
          <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

          {/* Содержимое вкладки */}
          {TabComponent && <TabComponent activeMethod={activeMethod} setActiveMethod={setActiveMethod} setActiveTab={setActiveTab} />}
        </main>
      </div>
      <Footer />
      <ChatWidget />
    </div>
  );
}

/**
 * Корневой компонент ТИТАН Аудит ТОРО v.200
 */
export default function App() {
  return (
    <FiltersProvider>
      <AppContent />
    </FiltersProvider>
  );
}
