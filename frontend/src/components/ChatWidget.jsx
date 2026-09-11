import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot, Loader2 } from 'lucide-react';
import api from '../services/api';

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hello! I\'m the PharmMedian Assistant. I can help you with batch tracking, return workflows, compliance questions, and navigating the platform. How can I help you today?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when chat panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage = { role: 'user', content: trimmed };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);

    try {
      const res = await api.post('/chatbot/message', {
        message: trimmed,
        conversation_history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.data.reply },
      ]);
    } catch (err) {
      console.error('Chatbot error:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'Something went wrong, please try again. If the issue persists, contact support.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Chat Panel */}
      {isOpen && (
        <div
          id="chat-widget-panel"
          style={{
            position: 'fixed',
            bottom: '96px',
            right: '24px',
            width: '380px',
            height: '500px',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            borderRadius: '20px',
            overflow: 'hidden',
            boxShadow:
              '0 20px 60px rgba(0,0,0,0.35), 0 0 0 1px rgba(30,58,138,0.25)',
            animation: 'chatSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          {/* Header */}
          <div
            style={{
              background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)',
              padding: '16px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(96,165,250,0.15)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '10px',
                  background: 'rgba(59,130,246,0.2)',
                  border: '1px solid rgba(96,165,250,0.35)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Bot size={18} color="#60a5fa" />
              </div>
              <div>
                <div
                  style={{
                    color: '#e2e8f0',
                    fontSize: '13px',
                    fontWeight: 700,
                    letterSpacing: '0.02em',
                  }}
                >
                  PharmMedian Assistant
                </div>
                <div
                  style={{
                    color: '#64748b',
                    fontSize: '10px',
                    fontFamily: 'monospace',
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                  }}
                >
                  Gemini AI &bull; Online
                </div>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                padding: '6px',
                cursor: 'pointer',
                color: '#94a3b8',
                display: 'flex',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.12)';
                e.currentTarget.style.color = '#e2e8f0';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                e.currentTarget.style.color = '#94a3b8';
              }}
            >
              <X size={16} />
            </button>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px',
              background: 'linear-gradient(180deg, #0f172a 0%, #111827 100%)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent:
                    msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '82%',
                    padding: '10px 14px',
                    borderRadius:
                      msg.role === 'user'
                        ? '14px 14px 4px 14px'
                        : '14px 14px 14px 4px',
                    fontSize: '12.5px',
                    lineHeight: '1.55',
                    fontWeight: 500,
                    ...(msg.role === 'user'
                      ? {
                          background:
                            'linear-gradient(135deg, #2563eb, #1d4ed8)',
                          color: '#ffffff',
                          boxShadow: '0 2px 8px rgba(37,99,235,0.25)',
                        }
                      : {
                          background: 'rgba(30,41,59,0.8)',
                          color: '#cbd5e1',
                          border: '1px solid rgba(71,85,105,0.4)',
                          boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
                        }),
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div
                  style={{
                    padding: '10px 16px',
                    borderRadius: '14px 14px 14px 4px',
                    background: 'rgba(30,41,59,0.8)',
                    border: '1px solid rgba(71,85,105,0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: '#64748b',
                    fontSize: '12px',
                    fontWeight: 500,
                  }}
                >
                  <Loader2
                    size={14}
                    style={{ animation: 'spin 1s linear infinite' }}
                  />
                  <span>Thinking&hellip;</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div
            style={{
              padding: '12px 14px',
              background: '#0f172a',
              borderTop: '1px solid rgba(71,85,105,0.3)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <input
              ref={inputRef}
              id="chat-widget-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your question..."
              disabled={isLoading}
              style={{
                flex: 1,
                padding: '10px 14px',
                borderRadius: '12px',
                border: '1px solid rgba(71,85,105,0.4)',
                background: 'rgba(30,41,59,0.6)',
                color: '#e2e8f0',
                fontSize: '12.5px',
                fontWeight: 500,
                outline: 'none',
                transition: 'border-color 0.15s',
              }}
              onFocus={(e) =>
                (e.target.style.borderColor = 'rgba(96,165,250,0.5)')
              }
              onBlur={(e) =>
                (e.target.style.borderColor = 'rgba(71,85,105,0.4)')
              }
            />
            <button
              id="chat-widget-send"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '12px',
                border: 'none',
                background:
                  !input.trim() || isLoading
                    ? 'rgba(71,85,105,0.3)'
                    : 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                color:
                  !input.trim() || isLoading ? '#475569' : '#ffffff',
                cursor:
                  !input.trim() || isLoading
                    ? 'not-allowed'
                    : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s',
                boxShadow:
                  !input.trim() || isLoading
                    ? 'none'
                    : '0 2px 8px rgba(37,99,235,0.3)',
              }}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Floating Action Button */}
      <button
        id="chat-widget-fab"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? 'Close chat' : 'Open chat'}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          border: 'none',
          background: 'linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)',
          color: '#60a5fa',
          cursor: 'pointer',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow:
            '0 6px 24px rgba(15,23,42,0.5), 0 0 0 3px rgba(96,165,250,0.15)',
          transition: 'transform 0.2s, box-shadow 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.08)';
          e.currentTarget.style.boxShadow =
            '0 8px 30px rgba(15,23,42,0.6), 0 0 0 4px rgba(96,165,250,0.25)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow =
            '0 6px 24px rgba(15,23,42,0.5), 0 0 0 3px rgba(96,165,250,0.15)';
        }}
      >
        {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
      </button>

      {/* Inline keyframe styles */}
      <style>{`
        @keyframes chatSlideUp {
          from {
            opacity: 0;
            transform: translateY(16px) scale(0.97);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        #chat-widget-panel ::-webkit-scrollbar {
          width: 4px;
        }
        #chat-widget-panel ::-webkit-scrollbar-track {
          background: transparent;
        }
        #chat-widget-panel ::-webkit-scrollbar-thumb {
          background: rgba(100,116,139,0.3);
          border-radius: 4px;
        }
      `}</style>
    </>
  );
}
