import { useState, useRef, useEffect, useCallback } from 'react';
import { C, GRADIENTS } from '../theme/arctic';
import { useFilters } from '../hooks/useFilters';

const BASE_URL = '';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content:
    'Привет! Я аналитик ТИТАН. Задайте вопрос по загруженным данным ТОРО.\n\nНапример: «Какие заказы с наибольшим перерасходом?» или «Сколько проблемного оборудования?»',
};

/** Иконка чата (SVG) */
function ChatIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

/** Иконка отправки */
function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

/** Иконка закрытия */
function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

/** Индикатор загрузки — три мигающие точки */
function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: 4, padding: '8px 0' }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            backgroundColor: C.accent,
            animation: `chatDotPulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

/**
 * ChatWidget — плавающий чат-бот аналитик ТИТАН
 */
export default function ChatWidget() {
  const { sessionId } = useFilters();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [llmAvailable, setLlmAvailable] = useState(null); // null = не проверяли
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Автопрокрутка при новых сообщениях
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Фокус на input при открытии
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Проверка доступности LLM при первом открытии
  useEffect(() => {
    if (isOpen && llmAvailable === null && sessionId) {
      checkLlm();
    }
  }, [isOpen, sessionId]);

  const checkLlm = async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: 'ping',
          history: [],
        }),
      });
      const data = await res.json();
      setLlmAvailable(data.llm_available);
    } catch {
      setLlmAvailable(false);
    }
  };

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading || !sessionId) return;

    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // Формируем историю (без welcome-сообщения)
      const history = messages
        .filter((m) => m !== WELCOME_MESSAGE)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await fetch(`${BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          history,
        }),
      });

      const data = await res.json();
      setLlmAvailable(data.llm_available);

      const assistantMsg = { role: 'assistant', content: data.reply || 'Нет ответа.' };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Ошибка: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId, messages]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* CSS-анимация для точек */}
      <style>{`
        @keyframes chatDotPulse {
          0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
          30% { opacity: 1; transform: scale(1.2); }
        }
        @keyframes chatSlideIn {
          from { opacity: 0; transform: translateY(16px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>

      {/* Кнопка-триггер */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 50,
          height: 50,
          borderRadius: '50%',
          background: `linear-gradient(135deg, ${C.accent}, #0ea5e9)`,
          border: 'none',
          color: '#fff',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          boxShadow: `0 4px 20px rgba(56,189,248,0.4)`,
          transition: 'transform 0.2s, box-shadow 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.08)';
          e.currentTarget.style.boxShadow = '0 6px 28px rgba(56,189,248,0.55)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 4px 20px rgba(56,189,248,0.4)';
        }}
        title="ТИТАН Аналитик"
      >
        <ChatIcon />
        {/* Индикатор доступности LLM */}
        {llmAvailable !== null && (
          <span
            style={{
              position: 'absolute',
              top: 2,
              right: 2,
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: llmAvailable ? C.success : C.dim,
              border: `2px solid ${C.bg}`,
            }}
          />
        )}
      </button>

      {/* Панель чата */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: 80,
            right: 24,
            width: 400,
            height: 500,
            backgroundColor: C.bg,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            zIndex: 999,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
            animation: 'chatSlideIn 0.25s ease-out',
            overflow: 'hidden',
          }}
        >
          {/* Заголовок */}
          <div
            style={{
              background: GRADIENTS.navbar,
              borderBottom: `2px solid ${C.accent}`,
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ChatIcon />
              <span style={{ fontWeight: 600, fontSize: 14, color: C.text }}>
                ТИТАН Аналитик
              </span>
              {llmAvailable !== null && (
                <span
                  style={{
                    fontSize: 10,
                    color: llmAvailable ? C.success : C.muted,
                    padding: '2px 6px',
                    borderRadius: 8,
                    backgroundColor: llmAvailable
                      ? 'rgba(52,211,153,0.12)'
                      : 'rgba(100,116,139,0.12)',
                  }}
                >
                  {llmAvailable ? 'LLM Online' : 'LLM Offline'}
                </span>
              )}
            </div>
            <button
              onClick={() => setIsOpen(false)}
              style={{
                background: 'none',
                border: 'none',
                color: C.muted,
                cursor: 'pointer',
                padding: 4,
                display: 'flex',
                alignItems: 'center',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = C.text)}
              onMouseLeave={(e) => (e.currentTarget.style.color = C.muted)}
            >
              <CloseIcon />
            </button>
          </div>

          {/* Область сообщений */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                }}
              >
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius:
                      msg.role === 'user'
                        ? '12px 12px 2px 12px'
                        : '12px 12px 12px 2px',
                    background:
                      msg.role === 'user'
                        ? `linear-gradient(135deg, ${C.accent}, #0ea5e9)`
                        : GRADIENTS.card,
                    color: msg.role === 'user' ? '#fff' : C.text,
                    fontSize: 13,
                    lineHeight: 1.5,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    border: msg.role === 'user' ? 'none' : `1px solid ${C.border}`,
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ alignSelf: 'flex-start' }}>
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: '12px 12px 12px 2px',
                    background: GRADIENTS.card,
                    border: `1px solid ${C.border}`,
                  }}
                >
                  <TypingIndicator />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Поле ввода */}
          <div
            style={{
              borderTop: `1px solid ${C.border}`,
              padding: '10px 12px',
              display: 'flex',
              gap: 8,
              alignItems: 'flex-end',
              flexShrink: 0,
              backgroundColor: C.surface,
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Задайте вопрос..."
              rows={1}
              style={{
                flex: 1,
                resize: 'none',
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                padding: '8px 12px',
                backgroundColor: C.bg,
                color: C.text,
                fontSize: 13,
                fontFamily: 'inherit',
                outline: 'none',
                maxHeight: 80,
                overflowY: 'auto',
              }}
              onFocus={(e) => (e.target.style.borderColor = C.accent)}
              onBlur={(e) => (e.target.style.borderColor = C.border)}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                border: 'none',
                background:
                  loading || !input.trim()
                    ? C.dim
                    : `linear-gradient(135deg, ${C.accent}, #0ea5e9)`,
                color: '#fff',
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                transition: 'background 0.2s',
              }}
            >
              <SendIcon />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
