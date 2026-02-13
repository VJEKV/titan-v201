/**
 * API клиент для FastAPI backend
 */

const BASE_URL = '';

export async function apiUpload(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Ошибка загрузки');
  }
  return res.json();
}

export async function apiGet(endpoint, params = {}) {
  const url = new URL(`${BASE_URL}${endpoint}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) {
      url.searchParams.set(k, typeof v === 'object' ? JSON.stringify(v) : v);
    }
  });

  const res = await fetch(url.toString());
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Ошибка ${res.status}`);
  }
  return res.json();
}

export async function apiDownload(endpoint, params = {}) {
  const url = new URL(`${BASE_URL}${endpoint}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) {
      url.searchParams.set(k, typeof v === 'object' ? JSON.stringify(v) : v);
    }
  });

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Ошибка скачивания');

  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `titan_export_${new Date().toISOString().slice(0,10)}.xlsx`;
  a.click();
  URL.revokeObjectURL(a.href);
}
