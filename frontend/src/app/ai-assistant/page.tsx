"use client";
import { useEffect, useState, useRef } from "react";
import { Bot, Send, Search, Sparkles, User, AlertCircle, RefreshCw } from "lucide-react";
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
  timestamp: Date;
}

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hello! I am the SISM AI Agent. I have real-time access to your inventory, storage layout, perishability metrics, and procurement needs via ChromaDB RAG. How can I help you today?",
      source: "system",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [refreshing, setRefreshing] = useState(false);

  const fetchInsights = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/ai/insights`);
      const data = await res.json();
      setInsights(data);
    } catch (e) {
      console.error(e);
    }
  };

  const generateInsights = async () => {
    setRefreshing(true);
    try {
      await fetch(`http://localhost:8000/api/ai/insights/generate`, { method: 'POST' });
      await fetchInsights();
    } catch (e) {
      console.error(e);
    }
    setRefreshing(false);
  };

  const handleDismiss = async (id: string) => {
    // Optimistically remove from UI
    setInsights(prev => prev.filter(i => i.insight_id !== id));
    try {
      await fetch(`http://localhost:8000/api/ai/insights/${id}/resolve`, { method: 'PUT' });
    } catch (e) {
      console.error("Failed to dismiss insight", e);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input;
    setInput("");
    setMessages(prev => [...prev, { role: 'user', content: userMsg, timestamp: new Date() }]);
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:8000/api/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.answer, 
        source: data.source,
        timestamp: new Date() 
      }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I couldn't reach the backend server.", timestamp: new Date() }]);
    }
    setLoading(false);
  };

  return (
    <div className="max-w-7xl mx-auto pb-10 flex flex-col lg:flex-row gap-6 h-[calc(100vh-120px)]">
      {/* Chat Interface */}
      <div className="flex-1 glass-panel flex flex-col h-full overflow-hidden">
        <div className="p-4 border-b border-slate-700/50 flex items-center gap-3 bg-slate-800/80">
          <div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">SISM Co-Pilot</h2>
            <p className="text-xs text-slate-400 flex items-center gap-1">
              Powered by <Sparkles className="w-3 h-3 text-emerald-400" /> Gemini & RAG
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.role === 'user' ? 'bg-blue-600' : 'bg-slate-700'}`}>
                {m.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-blue-400" />}
              </div>
              <div className={`p-4 rounded-xl shadow-md ${
                m.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-tr-sm' 
                  : 'glass-card text-slate-200 rounded-tl-sm prose prose-invert prose-p:leading-relaxed max-w-none'
              }`}>
                {m.role === 'assistant' ? (
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                ) : (
                  m.content
                )}
                {m.source && m.source !== 'system' && m.source !== 'validation' && (
                  <div className="mt-3 pt-2 border-t border-slate-700/50 text-[10px] text-slate-500 font-mono">
                    Source: {m.source}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3 max-w-[85%]">
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-blue-400" />
              </div>
              <div className="glass-card p-4 rounded-xl rounded-tl-sm flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-slate-800/80 border-t border-slate-700/50">
          <form onSubmit={sendMessage} className="relative flex items-center">
            <input 
              type="text" 
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about inventory, expiring items, or storage conflicts..." 
              className="w-full bg-slate-900 border border-slate-700 rounded-full py-3 pl-4 pr-12 text-slate-200 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50"
            />
            <button 
              type="submit"
              disabled={loading || !input.trim()}
              className="absolute right-2 p-2 bg-blue-600 text-white rounded-full hover:bg-blue-500 disabled:opacity-50 transition-all"
            >
              <Send className="w-4 h-4 shrink-0 -ml-0.5 mt-0.5" />
            </button>
          </form>
        </div>
      </div>

      {/* Proactive Insights Panel */}
      <div className="w-full lg:w-80 flex flex-col gap-4">
        <div className="glass-panel p-4 flex-1 overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" /> Agentic Insights
            </h3>
            <button 
              onClick={generateInsights} 
              disabled={refreshing}
              className={`text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 ${refreshing ? 'opacity-50' : ''}`}
            >
              <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} /> 
              {refreshing ? 'Analyzing...' : 'Refresh'}
            </button>
          </div>
          
          <div className="space-y-3">
            {insights.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-4">No unread insights. Run refresh to scan database.</p>
            ) : (
              insights.map(i => (
                <div key={i.insight_id} className={`p-3 rounded-xl border ${
                  i.severity === 'critical' ? 'bg-rose-500/10 border-rose-500/30' : 
                  i.severity === 'warning' ? 'bg-amber-500/10 border-amber-500/30' : 
                  'bg-blue-500/10 border-blue-500/30'
                }`}>
                  <div className="flex items-start gap-2 mb-1">
                    <AlertCircle className={`w-4 h-4 mt-0.5 shrink-0 ${
                      i.severity === 'critical' ? 'text-rose-400' : 
                      i.severity === 'warning' ? 'text-amber-400' : 'text-blue-400'
                    }`} />
                    <div className="text-sm text-slate-200">
                      <div className="prose prose-sm prose-invert">
                        <ReactMarkdown>{i.message}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 text-right">
                    <button 
                      onClick={() => handleDismiss(i.insight_id)}
                      className="text-xs text-slate-400 hover:text-white transition-colors"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
