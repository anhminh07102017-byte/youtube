"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Trash2, CheckCircle2, Loader2, AlertCircle, WifiOff, Copy, Check, RotateCcw } from "lucide-react";
import { getChatHistory, streamChatMessage, clearChatHistory, finalizeChatScript, checkChatHealth, getShortChatHistory, streamShortChat, finalizeShort } from "@/lib/api";
import type { ChatMessage } from "@/lib/api";

interface DraftTag { tag: string; code: string; label: string }

function extractDraftTags(text: string): DraftTag[] {
  const tags: DraftTag[] = [];
  const kbMatches = text.match(/\[KB:(\d+)\]/g);
  if (kbMatches) {
    for (const m of Array.from(new Set(kbMatches))) {
      const code = m.replace(/\[KB:|]/g, '');
      tags.push({ tag: "KB", code, label: "Kịch bản" });
    }
  }
  const ndMatches = text.match(/\[ND:(\d+)\]/g);
  if (ndMatches) {
    for (const m of Array.from(new Set(ndMatches))) {
      const code = m.replace(/\[ND:|]/g, '');
      tags.push({ tag: "ND", code, label: "Nội dung" });
    }
  }
  return tags;
}

interface ChatPanelProps { projectId: string; videoId: string; onFinalized?: () => void; chatType?: "video" | "short"; }

export function ChatPanel({ projectId, videoId, onFinalized, chatType = "video" }: ChatPanelProps) {
  const isShortChat = chatType === "short";
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [finalizing, setFinalizing] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, []);

  useEffect(() => {
    let mounted = true;
    const check = async () => { try { const h = await checkChatHealth(); if (mounted) setOnline(h.status === "ok"); } catch { if (mounted) setOnline(false); } };
    check(); const interval = setInterval(check, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  useEffect(() => {
    let mounted = true;
    const load = async () => { try { const data = isShortChat ? await getShortChatHistory(projectId, videoId) : await getChatHistory(projectId, videoId); if (mounted) { setMessages(data.messages || []); setError(null); } } catch { if (mounted && online !== false) setError("Không tải được lịch sử chat"); } };
    if (online !== false) load();
    return () => { mounted = false; };
  }, [projectId, videoId, online]);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const adjustTextarea = () => { const ta = textareaRef.current; if (ta) { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 150) + "px"; } };

  const handleSend = async () => {
    const text = input.trim(); if (!text || sending) return;
    setInput(""); setSending(true); setError(null); setStreamingText("");
    const userMsg: ChatMessage = { role: "user", content: text, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    try {
      const streamFn = isShortChat ? streamShortChat : streamChatMessage;
      await streamFn(
        projectId, videoId, text,
        (delta) => { setStreamingText((prev) => prev + delta); },
        (fullText) => {
          setStreamingText("");
          setMessages((prev) => [...prev, { role: "assistant", content: fullText, timestamp: new Date().toISOString() }]);
          setSending(false);
        },
        (err) => {
          setStreamingText("");
          setError(`Gửi tin nhắn thất bại: ${err}`);
          setSending(false);
        },
      );
    } catch {
      setStreamingText("");
      setError("Gửi tin nhắn thất bại. Chat Bridge có đang chạy không?");
      setMessages((prev) => prev.slice(0, -1));
      setSending(false);
    }
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } };
  const handleClear = async () => {
    if (!confirm("Xóa toàn bộ lịch sử chat?")) return;
    try {
      if (isShortChat) {
        await fetch(`${process.env.NEXT_PUBLIC_CHAT_URL || 'http://localhost:8001'}/api/chat/${projectId}/${videoId}/short`, { method: 'DELETE' });
      } else {
        await clearChatHistory(projectId, videoId);
      }
      setMessages([]); setError(null);
    } catch { setError("Xóa thất bại"); }
  };
  const handleSaveDraft = async (tag?: string, code?: string) => {
    setFinalizing(true); setError(null);
    try {
      const kbCode = tag === "KB" ? code : undefined;
      const ndCode = tag === "ND" ? code : undefined;
      const result = isShortChat
        ? await finalizeShort(projectId, videoId)
        : await finalizeChatScript(projectId, videoId, kbCode, ndCode);
      const savedParts = Object.keys(result.saved || {});
      const names = savedParts.map(k => k === "script" ? "kịch bản" : "nội dung").join(" + ");
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: `Đã chốt ${names}${code ? ` (${tag}:${code})` : ""}! Chuyển sang tab tương ứng để xem.`,
        timestamp: new Date().toISOString(),
      }]);
      onFinalized?.();
    } catch {
      setError("Chốt thất bại. Chưa có bản kịch bản/nội dung nào trong chat.");
    } finally { setFinalizing(false); }
  };
  const handleCopyCommand = () => { navigator.clipboard.writeText("cd ~/Youtube/video-factory && python3 chat_bridge.py"); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  if (online === false) {
    return (
      <div className="bg-white rounded-2xl p-8 text-center">
        <div className="w-14 h-14 rounded-2xl bg-orange-50 flex items-center justify-center mx-auto mb-4"><WifiOff className="w-7 h-7 text-orange-400" /></div>
        <p className="text-[15px] font-semibold text-gray-700 mb-1">Chat Bridge chưa chạy</p>
        <p className="text-[13px] text-gray-400 mb-5">Cần chạy trên máy host để kết nối Claude Code CLI.</p>
        <div className="bg-gray-50 rounded-xl p-4 max-w-md mx-auto">
          <p className="text-[11px] text-gray-400 mb-2">Chạy lệnh sau trong terminal:</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-[12px] text-indigo-600 font-mono bg-indigo-50 px-3 py-2 rounded-lg">cd ~/Youtube/video-factory && python3 chat_bridge.py</code>
            <button onClick={handleCopyCommand} className="p-2 rounded-lg bg-indigo-50 text-indigo-500 hover:bg-indigo-100 transition-colors" title="Copy">
              {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (online === null) return <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-indigo-500 animate-spin" /></div>;

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] lg:h-[calc(100vh-280px)] min-h-[350px]">
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[11px] text-gray-400 font-medium">Claude Code — đang hoạt động</span>
        </div>
        <div className="flex gap-2">
          <button onClick={handleClear} disabled={messages.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-gray-100 text-gray-500 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Xóa lịch sử chat và bắt đầu cuộc trò chuyện mới">
            <RotateCcw className="w-3.5 h-3.5" /> Chat mới
          </button>
          <button onClick={() => handleSaveDraft()} disabled={finalizing || messages.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Lưu bản mới nhất (kịch bản + nội dung)">
            {finalizing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Chốt
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center mx-auto mb-3"><Send className="w-5 h-5 text-indigo-500" /></div>
            <p className="text-[14px] font-semibold text-gray-600 mb-1">Bắt đầu lên kịch bản</p>
            <p className="text-[12px] text-gray-400">Chat với Claude. Khi hài lòng, nhấn &quot;Chốt kịch bản&quot;.</p>
          </div>
        )}
        {messages.map((msg, i) => {
          const drafts = msg.role === "assistant" ? extractDraftTags(msg.content) : [];
          return (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.role === "user" ? "bg-indigo-500 text-white" : "bg-white text-gray-700 border border-gray-100"}`}>
                <pre className="text-[13px] whitespace-pre-wrap font-[inherit] leading-relaxed break-words">{msg.content}</pre>
                {drafts.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-100">
                    {drafts.map((d) => (
                      <button key={`${d.tag}:${d.code}`} onClick={() => handleSaveDraft(d.tag, d.code)} disabled={finalizing}
                        className={`flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg disabled:opacity-40 transition-colors ${
                          d.tag === "KB"
                            ? "bg-indigo-50 text-indigo-600 hover:bg-indigo-100"
                            : "bg-emerald-50 text-emerald-600 hover:bg-emerald-100"
                        }`}>
                        <CheckCircle2 className="w-3 h-3" /> Chốt {d.label} ({d.tag}:{d.code})
                      </button>
                    ))}
                  </div>
                )}
                <p className={`text-[10px] mt-1.5 ${msg.role === "user" ? "text-indigo-200" : "text-gray-400"}`}>{new Date(msg.timestamp).toLocaleTimeString()}</p>
              </div>
            </div>
          );
        })}
        {sending && (
          <div className="flex justify-start">
            <div className="max-w-[80%] bg-white border border-gray-100 rounded-2xl px-4 py-3">
              {streamingText ? (
                <pre className="text-[13px] whitespace-pre-wrap font-[inherit] leading-relaxed break-words text-gray-700">{streamingText}<span className="inline-block w-1.5 h-4 bg-indigo-500 rounded-sm animate-pulse ml-0.5 align-text-bottom" /></pre>
              ) : (
                <div className="flex items-center gap-2 text-[13px] text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
                  Claude đang suy nghĩ...
                </div>
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="flex items-center gap-2 px-3 py-2 text-[11px] text-rose-500 bg-rose-50 rounded-lg mb-2">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> {error}
        </div>
      )}

      <div className="border-t border-gray-100 pt-3">
        <div className="flex gap-2">
          <textarea ref={textareaRef} value={input} onChange={(e) => { setInput(e.target.value); adjustTextarea(); }} onKeyDown={handleKeyDown}
            placeholder="Nhập tin nhắn... (Enter gửi, Shift+Enter xuống dòng)" disabled={sending} rows={1}
            className="flex-1 resize-none bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-[13px] text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 disabled:opacity-50 transition-all" />
          <button onClick={handleSend} disabled={!input.trim() || sending}
            className="px-4 py-3 bg-indigo-500 text-white rounded-xl hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0 shadow-sm">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
