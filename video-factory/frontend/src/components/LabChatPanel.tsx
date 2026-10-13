"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Send,
  Loader2,
  AlertCircle,
  WifiOff,
  Copy,
  Check,
  Save,
  BookOpen,
  Palette,
  Plus,
  Trash2,
  MessageSquare,
} from "lucide-react";
import {
  getLabSessions,
  createLabSession,
  deleteLabSession,
  getLabSessionHistory,
  streamLabChat,
  saveLabOutput,
  getLabOutputs,
  checkChatHealth,
} from "@/lib/api";
import type { ChatMessage, LabSession, LabOutput } from "@/lib/api";

type LabType = "storytelling" | "styles";

interface LabTag {
  tag: string;
  code: string;
  label: string;
}

function extractLabTags(text: string, labType: LabType): LabTag[] {
  const tags: LabTag[] = [];
  if (labType === "storytelling") {
    const matches = text.match(/\[PROFILE:(\d+)\]/g);
    if (matches) {
      for (const m of Array.from(new Set(matches))) {
        const code = m.replace(/\[PROFILE:|]/g, "");
        tags.push({ tag: "PROFILE", code, label: "Storytelling Profile" });
      }
    }
  } else {
    const imgMatches = text.match(/\[IMG_STYLE:(\d+)\]/g);
    if (imgMatches) {
      for (const m of Array.from(new Set(imgMatches))) {
        const code = m.replace(/\[IMG_STYLE:|]/g, "");
        tags.push({ tag: "IMG_STYLE", code, label: "Image Style" });
      }
    }
    const editMatches = text.match(/\[EDIT_STYLE:(\d+)\]/g);
    if (editMatches) {
      for (const m of Array.from(new Set(editMatches))) {
        const code = m.replace(/\[EDIT_STYLE:|]/g, "");
        tags.push({ tag: "EDIT_STYLE", code, label: "Edit Style" });
      }
    }
  }
  return tags;
}

function timeAgo(dateStr: string): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
}

interface LabChatPanelProps {
  labType: LabType;
}

export function LabChatPanel({ labType }: LabChatPanelProps) {
  const [sessions, setSessions] = useState<LabSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [saving, setSaving] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [outputs, setOutputs] = useState<LabOutput[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Health check
  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const h = await checkChatHealth();
        if (mounted) setOnline(h.status === "ok");
      } catch {
        if (mounted) setOnline(false);
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Load sessions list
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoadingSessions(true);
        const data = await getLabSessions(labType);
        if (mounted) {
          setSessions(data.sessions || []);
          // Auto-select first session if none active
          if (!activeSessionId && data.sessions?.length > 0) {
            setActiveSessionId(data.sessions[0].id);
          }
        }
      } catch {
        /* ignore */
      } finally {
        if (mounted) setLoadingSessions(false);
      }
    };
    if (online !== false) load();
    return () => {
      mounted = false;
    };
  }, [labType, online]);

  // Load session messages when active session changes
  useEffect(() => {
    let mounted = true;
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    const load = async () => {
      try {
        const data = await getLabSessionHistory(labType, activeSessionId);
        if (mounted) {
          setMessages(data.messages || []);
          setError(null);
        }
      } catch {
        if (mounted) setError("Không tải được lịch sử chat");
      }
    };
    if (online !== false) load();
    return () => {
      mounted = false;
    };
  }, [labType, activeSessionId, online]);

  // Load existing outputs
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const data = await getLabOutputs(labType);
        if (mounted) setOutputs(data.outputs || []);
      } catch {
        /* ignore */
      }
    };
    if (online !== false) load();
    return () => {
      mounted = false;
    };
  }, [labType, online]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText, scrollToBottom]);

  const adjustTextarea = () => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 150) + "px";
    }
  };

  const refreshSessions = async () => {
    try {
      const data = await getLabSessions(labType);
      setSessions(data.sessions || []);
    } catch {
      /* ignore */
    }
  };

  const handleNewSession = async () => {
    try {
      const session = await createLabSession(labType);
      setSessions((prev) => [
        {
          id: session.id,
          title: session.title,
          created_at: session.created_at,
          updated_at: session.updated_at,
          message_count: 0,
        },
        ...prev,
      ]);
      setActiveSessionId(session.id);
      setMessages([]);
      setError(null);
    } catch {
      setError("Tạo chat mới thất bại");
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm("Xóa đoạn chat này?")) return;
    try {
      await deleteLabSession(labType, sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch {
      setError("Xóa thất bại");
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending || !activeSessionId) return;
    setInput("");
    setSending(true);
    setError(null);
    setStreamingText("");
    const userMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    try {
      await streamLabChat(
        labType,
        activeSessionId,
        text,
        (delta) => {
          setStreamingText((prev) => prev + delta);
        },
        (fullText) => {
          setStreamingText("");
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: fullText,
              timestamp: new Date().toISOString(),
            },
          ]);
          setSending(false);
          refreshSessions(); // Refresh to update title & message count
        },
        (err) => {
          setStreamingText("");
          setError(`Gửi tin nhắn thất bại: ${err}`);
          setSending(false);
        }
      );
    } catch {
      setStreamingText("");
      setError("Gửi tin nhắn thất bại. Chat Bridge có đang chạy không?");
      setMessages((prev) => prev.slice(0, -1));
      setSending(false);
    }
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSave = async (tag: string, code: string) => {
    if (!activeSessionId) return;
    setSaving(true);
    setError(null);
    try {
      const result = await saveLabOutput(labType, activeSessionId, tag, code);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Đã lưu ${result.name} (${result.category}/${result.template_id})! Có thể áp dụng vào project từ trang Tài nguyên.`,
          timestamp: new Date().toISOString(),
        },
      ]);
      const data = await getLabOutputs(labType);
      setOutputs(data.outputs || []);
    } catch {
      setError(
        "Lưu thất bại. Đảm bảo AI đã xuất đúng format JSON trong tag."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(
      "cd ~/Youtube/video-factory && python3 chat_bridge.py"
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const labConfig = {
    storytelling: {
      title: "Phòng lab Kể chuyện",
      emptyTitle: "Phân tích cách kể chuyện",
      emptyDesc:
        'Gửi transcript hoặc mô tả cách kể chuyện. Khi hài lòng, nói "Lưu" để tạo profile.',
      icon: BookOpen,
    },
    styles: {
      title: "Phòng lab Phong cách",
      emptyTitle: "Phân tích phong cách",
      emptyDesc:
        'Mô tả phong cách hình ảnh hoặc cách edit. Nói "Lưu hình ảnh" hoặc "Lưu edit" để tạo template.',
      icon: Palette,
    },
  };

  const config = labConfig[labType];

  if (online === false) {
    return (
      <div className="bg-white rounded-2xl p-8 text-center">
        <div className="w-14 h-14 rounded-2xl bg-orange-50 flex items-center justify-center mx-auto mb-4">
          <WifiOff className="w-7 h-7 text-orange-400" />
        </div>
        <p className="text-[15px] font-semibold text-gray-700 mb-1">
          Chat Bridge chưa chạy
        </p>
        <p className="text-[13px] text-gray-400 mb-5">
          Cần chạy trên máy host để kết nối Claude Code CLI.
        </p>
        <div className="bg-gray-50 rounded-xl p-4 max-w-md mx-auto">
          <p className="text-[11px] text-gray-400 mb-2">
            Chạy lệnh sau trong terminal:
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-[12px] text-indigo-600 font-mono bg-indigo-50 px-3 py-2 rounded-lg">
              cd ~/Youtube/video-factory && python3 chat_bridge.py
            </code>
            <button
              onClick={handleCopyCommand}
              className="p-2 rounded-lg bg-indigo-50 text-indigo-500 hover:bg-indigo-100 transition-colors"
              title="Copy"
            >
              {copied ? (
                <Check className="w-4 h-4 text-emerald-500" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (online === null)
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );

  return (
    <div className="flex gap-4 h-[calc(100vh-180px)]">
      {/* Left sidebar — Sessions list */}
      <div className="w-64 flex-shrink-0 flex flex-col bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {/* New session button */}
        <div className="p-3 border-b border-gray-100">
          <button
            onClick={handleNewSession}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-[12px] font-semibold text-white bg-violet-500 rounded-xl hover:bg-violet-600 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> Chat mới
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingSessions ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8 px-3">
              <MessageSquare className="w-8 h-8 text-gray-200 mx-auto mb-2" />
              <p className="text-[12px] text-gray-400">
                Chưa có chat nào.
              </p>
              <p className="text-[11px] text-gray-300 mt-1">
                Bấm &quot;Chat mới&quot; để bắt đầu.
              </p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`group flex items-start gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
                  activeSessionId === session.id
                    ? "bg-violet-50 border border-violet-200"
                    : "hover:bg-gray-50 border border-transparent"
                }`}
                onClick={() => setActiveSessionId(session.id)}
              >
                <MessageSquare
                  className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                    activeSessionId === session.id
                      ? "text-violet-500"
                      : "text-gray-300"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p
                    className={`text-[12px] font-medium truncate ${
                      activeSessionId === session.id
                        ? "text-violet-700"
                        : "text-gray-600"
                    }`}
                  >
                    {session.title}
                  </p>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    {timeAgo(session.updated_at)} · {session.message_count} tin
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSession(session.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-gray-300 hover:text-rose-500 hover:bg-rose-50 transition-all"
                  title="Xóa"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {!activeSessionId ? (
          /* No session selected */
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-14 h-14 rounded-2xl bg-violet-50 flex items-center justify-center mx-auto mb-4">
                <config.icon className="w-7 h-7 text-violet-400" />
              </div>
              <p className="text-[15px] font-semibold text-gray-600 mb-1">
                {config.emptyTitle}
              </p>
              <p className="text-[12px] text-gray-400 max-w-sm">
                {config.emptyDesc}
              </p>
              <button
                onClick={handleNewSession}
                className="mt-4 flex items-center gap-2 px-4 py-2.5 text-[12px] font-semibold text-white bg-violet-500 rounded-xl hover:bg-violet-600 transition-colors mx-auto shadow-sm"
              >
                <Plus className="w-4 h-4" /> Tạo chat mới
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[11px] text-gray-400 font-medium">
                  Claude Code — {config.title}
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-4 space-y-3">
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <div className="w-12 h-12 rounded-xl bg-violet-50 flex items-center justify-center mx-auto mb-3">
                    <config.icon className="w-5 h-5 text-violet-500" />
                  </div>
                  <p className="text-[14px] font-semibold text-gray-600 mb-1">
                    {config.emptyTitle}
                  </p>
                  <p className="text-[12px] text-gray-400 max-w-md mx-auto">
                    {config.emptyDesc}
                  </p>
                </div>
              )}
              {messages.map((msg, i) => {
                const drafts =
                  msg.role === "assistant"
                    ? extractLabTags(msg.content, labType)
                    : [];
                return (
                  <div
                    key={i}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                        msg.role === "user"
                          ? "bg-violet-500 text-white"
                          : "bg-white text-gray-700 border border-gray-100"
                      }`}
                    >
                      <pre className="text-[13px] whitespace-pre-wrap font-[inherit] leading-relaxed break-words">
                        {msg.content}
                      </pre>
                      {drafts.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-100">
                          {drafts.map((d) => (
                            <button
                              key={`${d.tag}:${d.code}`}
                              onClick={() => handleSave(d.tag, d.code)}
                              disabled={saving}
                              className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-violet-50 text-violet-600 hover:bg-violet-100 disabled:opacity-40 transition-colors"
                            >
                              <Save className="w-3 h-3" /> Lưu {d.label} (
                              {d.tag}:{d.code})
                            </button>
                          ))}
                        </div>
                      )}
                      <p
                        className={`text-[10px] mt-1.5 ${
                          msg.role === "user"
                            ? "text-violet-200"
                            : "text-gray-400"
                        }`}
                      >
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                );
              })}
              {sending && (
                <div className="flex justify-start">
                  <div className="max-w-[80%] bg-white border border-gray-100 rounded-2xl px-4 py-3">
                    {streamingText ? (
                      <pre className="text-[13px] whitespace-pre-wrap font-[inherit] leading-relaxed break-words text-gray-700">
                        {streamingText}
                        <span className="inline-block w-1.5 h-4 bg-violet-500 rounded-sm animate-pulse ml-0.5 align-text-bottom" />
                      </pre>
                    ) : (
                      <div className="flex items-center gap-2 text-[13px] text-gray-400">
                        <Loader2 className="w-4 h-4 animate-spin text-violet-500" />
                        Claude đang phân tích...
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 px-3 py-2 text-[11px] text-rose-500 bg-rose-50 rounded-lg mb-2">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> {error}
              </div>
            )}

            {/* Input */}
            <div className="border-t border-gray-100 pt-3">
              <div className="flex gap-2">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    adjustTextarea();
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Nhập tin nhắn... (Enter gửi, Shift+Enter xuống dòng)"
                  disabled={sending}
                  rows={1}
                  className="flex-1 resize-none bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-[13px] text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-100 focus:border-violet-300 disabled:opacity-50 transition-all"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || sending}
                  className="px-4 py-3 bg-violet-500 text-white rounded-xl hover:bg-violet-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0 shadow-sm"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Right sidebar — saved outputs */}
      <div className="w-64 flex-shrink-0 bg-white rounded-2xl border border-gray-100 p-4 overflow-y-auto">
        <h3 className="text-[13px] font-semibold text-gray-700 mb-3">
          {labType === "storytelling"
            ? "Profiles đã tạo"
            : "Templates đã tạo"}
        </h3>
        {outputs.length === 0 ? (
          <p className="text-[12px] text-gray-400">
            Chưa có. Phân tích và nói &quot;Lưu&quot; để tạo.
          </p>
        ) : (
          <div className="space-y-2">
            {outputs.map((o) => (
              <div
                key={o.id}
                className="p-3 rounded-xl bg-gray-50 border border-gray-100"
              >
                <p className="text-[12px] font-semibold text-gray-700">
                  {o.name}
                </p>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  {o.description}
                </p>
                <span className="inline-block mt-1.5 px-2 py-0.5 text-[10px] font-medium rounded-md bg-violet-50 text-violet-500">
                  {o.category}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
