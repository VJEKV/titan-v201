import { useState, useRef } from 'react';
import { C, GRADIENTS } from '../theme/arctic';
import { apiUpload } from '../api/client';
import { useFilters } from '../hooks/useFilters';

/**
 * Экран загрузки файла
 */
export default function UploadScreen() {
  const { setSessionId, setFileInfo } = useFilters();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef();

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await apiUpload(file);
      setSessionId(result.session_id);
      setFileInfo({
        name: file.name,
        rows: result.rows,
        columns: result.columns,
        time: result.processing_time,
        format: result.format,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '80vh',
      padding: 40,
    }}>
      <h1 style={{ fontSize: 36, fontWeight: 700, color: C.accent, marginBottom: 8 }}>
        ТИТАН
      </h1>
      <p style={{ fontSize: 16, color: C.muted, marginBottom: 40 }}>
        Аудит ТОРО v.200 — Загрузите файл выгрузки SAP
      </p>

      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files[0]); }}
        onClick={() => fileRef.current?.click()}
        style={{
          width: 500,
          maxWidth: '90vw',
          padding: '60px 40px',
          background: dragOver ? `rgba(56,189,248,0.1)` : GRADIENTS.card,
          border: `2px dashed ${dragOver ? C.accent : C.border}`,
          borderRadius: 16,
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          style={{ display: 'none' }}
          onChange={e => handleUpload(e.target.files[0])}
        />

        {uploading ? (
          <div>
            <div style={{ fontSize: 24, marginBottom: 12 }}>⏳</div>
            <p style={{ color: C.accent }}>Обработка данных...</p>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📂</div>
            <p style={{ color: C.text, fontSize: 16, marginBottom: 8 }}>
              Перетащите файл сюда
            </p>
            <p style={{ color: C.muted, fontSize: 13 }}>
              или нажмите для выбора (.xlsx, .csv)
            </p>
          </div>
        )}
      </div>

      {error && (
        <div style={{
          marginTop: 20, padding: '12px 20px',
          background: 'rgba(244,63,94,0.1)', border: `1px solid ${C.danger}`,
          borderRadius: 8, color: C.danger, fontSize: 13,
        }}>
          {error}
        </div>
      )}
    </div>
  );
}
