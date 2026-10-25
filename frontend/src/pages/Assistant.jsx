import { useEffect, useRef, useState } from 'react';
import {
  Bot,
  BrainCircuit,
  Eye,
  HelpCircle,
  Info,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { deleteConversation, loadConversation, sendChatMessage } from '../services/chatbotApi';

const welcomeMessage = {
  role: 'assistant',
  content:
    "Hello! I'm your RetinalAI Assistant. I'm here to assist you with Diabetic Retinopathy information, explain AI predictions (including YOLO lesion detection and Grad-CAM maps), and guide you through using this platform. How can I help you today?",
};

const suggestedTopics = [
  {
    category: 'Diabetic Retinopathy',
    icon: Eye,
    questions: [
      'What is diabetic retinopathy?',
      'What are hard exudates and microaneurysms?',
      'What are the 5 stages of diabetic retinopathy?',
    ],
  },
  {
    category: 'AI & Explainability',
    icon: BrainCircuit,
    questions: [
      'What is Grad-CAM in RetinalAI?',
      'How does the Retinal Attention Map work?',
      'How does YOLO detect retinal lesions?',
    ],
  },
  {
    category: 'Platform Guidance',
    icon: HelpCircle,
    questions: [
      'How do I upload a fundus photo?',
      'Where can I download my medical report?',
      'How does the analysis workflow operate?',
    ],
  },
];

export default function Assistant() {
  const { currentUser } = useAuth();
  const storageKey = `retinaiq-chat:${currentUser?.id || 'anonymous'}`;

  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([welcomeMessage]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Load existing conversation on mount
  useEffect(() => {
    let isMounted = true;
    const savedId = window.localStorage.getItem(storageKey);

    loadConversation(savedId)
      .then((data) => {
        if (!isMounted) return;
        setConversationId(data.conversation_id);
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
        } else {
          setMessages([welcomeMessage]);
        }
      })
      .catch(() => {
        if (!isMounted) return;
        setMessages([welcomeMessage]);
      })
      .finally(() => {
        if (isMounted) setIsLoadingHistory(false);
      });

    return () => {
      isMounted = false;
    };
  }, [storageKey]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleSend = async (e, customText = '') => {
    e?.preventDefault();
    const textToSend = (customText || input).trim();
    if (!textToSend || isSending) return;

    setInput('');
    setError('');

    // Optimistically append user message
    setMessages((prev) => [...prev, { role: 'user', content: textToSend }]);
    setIsSending(true);

    try {
      const data = await sendChatMessage(textToSend, conversationId);
      setConversationId(data.conversation_id);
      window.localStorage.setItem(storageKey, data.conversation_id);

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          category: data.category,
        },
      ]);
    } catch (err) {
      setError(err.message || 'Failed to send message. Please try again.');
    } finally {
      setIsSending(false);
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  };

  const handleNewChat = async () => {
    if (messages.length > 1 && !window.confirm('Start a new chat session? This will clear your current conversation.')) {
      return;
    }

    if (conversationId) {
      await deleteConversation(conversationId).catch(() => {});
    }

    window.localStorage.removeItem(storageKey);
    setConversationId(null);
    setMessages([welcomeMessage]);
    setError('');
    setTimeout(() => textareaRef.current?.focus(), 100);
  };

  return (
    <div className="mx-auto max-w-[1380px] px-4 py-6 sm:px-6 lg:px-8">
      {/* Top Header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3.5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#0F2747] text-white shadow-md shadow-[#0F2747]/10">
            <Bot className="h-6 w-6 text-sky-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-[#0F2747] sm:text-3xl">
                Chatbot Assistant
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Active
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-500 sm:text-sm">
              Instant AI answers on Diabetic Retinopathy, Explainable AI (Grad-CAM), and platform workflows
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleNewChat}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-rose-600"
            title="Start new chat"
          >
            <Plus className="h-4 w-4" />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Sidebar topics + Chat conversation */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Topics & Help Panel */}
        <aside className="order-2 lg:order-1 lg:col-span-4 xl:col-span-3 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,39,71,0.04)]">
            <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-700">
              <Sparkles className="h-4 w-4 text-sky-600" />
              Suggested Questions
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Click any question below to immediately ask the assistant:
            </p>

            <div className="mt-4 space-y-4">
              {suggestedTopics.map((topic) => {
                const TopicIcon = topic.icon;
                return (
                  <div key={topic.category} className="space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-[#0F2747]">
                      <TopicIcon className="h-3.5 w-3.5 text-sky-600" />
                      <span>{topic.category}</span>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      {topic.questions.map((q) => (
                        <button
                          key={q}
                          type="button"
                          disabled={isSending}
                          onClick={(e) => handleSend(e, q)}
                          className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 text-left text-xs text-slate-700 transition hover:border-sky-200 hover:bg-sky-50/80 hover:text-sky-900 disabled:opacity-50"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-sky-100 bg-sky-50/60 p-4">
            <div className="flex gap-2.5">
              <Info className="h-4 w-4 shrink-0 text-sky-700" />
              <div className="text-xs text-slate-600 leading-relaxed">
                <strong className="block text-sky-950 font-semibold mb-0.5">Disclaimer:</strong>
                This AI assistant provides educational insights and explanations. It does not replace professional medical diagnosis from a licensed ophthalmologist.
              </div>
            </div>
          </div>
        </aside>

        {/* Right Main Chat Container */}
        <section className="order-1 lg:order-2 lg:col-span-8 xl:col-span-9 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_12px_34px_rgba(15,39,71,0.06)] overflow-hidden min-h-[580px] h-[calc(100vh-210px)] max-h-[820px]">
          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-slate-50/40">
            {isLoadingHistory ? (
              <div className="flex h-full items-center justify-center">
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <RefreshCw className="h-4 w-4 animate-spin text-sky-600" />
                  <span>Loading conversation history...</span>
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, idx) => {
                  const isUser = msg.role === 'user';
                  return (
                    <div
                      key={idx}
                      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                    >
                      {!isUser && (
                        <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-[#0F2747] text-white shadow-sm mt-0.5">
                          <Bot className="h-4 w-4 text-sky-300" />
                        </div>
                      )}

                      <div
                        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                          isUser
                            ? 'bg-[#1677FF] text-white rounded-br-none'
                            : 'bg-white border border-slate-200/90 text-slate-800 rounded-bl-none'
                        }`}
                      >
                        {msg.category && !isUser && (
                          <div className="mb-1.5">
                            <span className="inline-block rounded-md bg-sky-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-sky-700">
                              {msg.category}
                            </span>
                          </div>
                        )}
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      </div>

                      {isUser && (
                        <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-sky-100 text-sky-800 text-xs font-bold mt-0.5">
                          {currentUser?.fullName?.charAt(0) || 'U'}
                        </div>
                      )}
                    </div>
                  );
                })}

                {isSending && (
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[#0F2747] text-white shadow-sm">
                      <Bot className="h-4 w-4 text-sky-300 animate-pulse" />
                    </div>
                    <div className="rounded-2xl rounded-bl-none border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm flex items-center gap-2">
                      <span className="inline-block h-2 w-2 rounded-full bg-sky-500 animate-bounce" />
                      <span className="inline-block h-2 w-2 rounded-full bg-sky-500 animate-bounce [animation-delay:0.2s]" />
                      <span className="inline-block h-2 w-2 rounded-full bg-sky-500 animate-bounce [animation-delay:0.4s]" />
                      <span className="ml-1 text-xs font-medium text-slate-500">Generating response...</span>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="flex items-center justify-between rounded-xl bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
                    <span>{error}</span>
                    <button
                      type="button"
                      onClick={() => setError('')}
                      className="p-1 hover:text-rose-900"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Chat Input Bar */}
          <div className="border-t border-slate-200 bg-white p-3 sm:p-4">
            <form onSubmit={handleSend} className="space-y-2">
              <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50/70 p-2 focus-within:border-sky-400 focus-within:bg-white focus-within:ring-2 focus-within:ring-sky-100 transition">
                <textarea
                  ref={textareaRef}
                  id="assistant-chat-input"
                  value={input}
                  onChange={(e) => setInput(e.target.value.slice(0, 1500))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend(e);
                    }
                  }}
                  rows={2}
                  placeholder="Ask a question about Diabetic Retinopathy, Grad-CAM, or this platform..."
                  className="max-h-28 min-h-[44px] flex-1 resize-none border-0 bg-transparent px-2.5 py-1 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isSending}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#1677FF] text-white shadow-sm transition hover:bg-[#0868ed] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
                  title="Send message (Enter)"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-center justify-between px-1 text-[11px] text-slate-400">
                <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for a new line</span>
                <span>{input.length}/1500</span>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
