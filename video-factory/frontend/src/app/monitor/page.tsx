"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity,
  MessageSquare,
  Image,
  Users,
  ListChecks,
  Wifi,
  WifiOff,
  Cpu,
  CircleDot,
  CheckCircle2,
  XCircle,
  Loader2,
  Trash2,
  Brain,
  Pen,
} from "lucide-react";
import {
  MonitorActivity,
  MonitorStatus,
  MonitorJob,
  getMonitorStatus,
  getMonitorActivities,
  connectMonitorStream,
} from "@/lib/api";

const CATEGORIES = [
  { key: "", label: "Tất cả", icon: Activity, color: "text-gray-600", bg: "bg-gray-50" },
  { key: "chat", label: "Chat", icon: MessageSquare, color: "text-blue-600", bg: "bg-blue-50" },
  { key: "prompt", label: "Prompt", icon: Image, color: "text-purple-600", bg: "bg-purple-50" },
  { key: "character", label: "Nhân vật", icon: Users, color: "text-amber-600", bg: "bg-amber-50" },
  { key: "shotlist", label: "Shot list", icon: ListChecks, color: "text-cyan-600", bg: "bg-cyan-50" },
];

function categoryMeta(cat: string) {
  return CATEGORIES.find((c) => c.key === cat) || CATEGORIES[0];
}

function statusIcon(status: string) {
  switch (status) {
    case "success":
      return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />;
    case "error":
      return <XCircle className="w-3.5 h-3.5 text-rose-500" />;
    case "working":
      return <Loader2 className="w-3.5 h-3.5 text-indigo-500 animate-spin" />;
    default:
      return <CircleDot className="w-3.5 h-3.5 text-gray-400" />;
  }
}

function statusColor(status: string) {
  switch (status) {
    case "success":
      return "bg-emerald-50 border-emerald-100";
    case "error":
      return "bg-rose-50 border-rose-100";
    case "working":
      return "bg-indigo-50 border-indigo-100";
    default:
      return "bg-white border-gray-100";
  }
}

function timeAgo(ts: string) {
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 1000) return "vừa xong";
  if (diff < 60000) return `${Math.floor(diff / 1000)}s trước`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}p trước`;
  return `${Math.floor(diff / 3600000)}h trước`;
}

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function MonitorPage() {
  const [status, setStatus] = useState<MonitorStatus | null>(null);
  const [activities, setActivities] = useState<MonitorActivity[]>([]);
  const [connected, setConnected] = useState(false);
  const [bridgeOnline, setBridgeOnline] = useState<boolean | null>(null);
  const [activeFilter, setActiveFilter] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);
  const disconnectRef = useRef<(() => void) | null>(null);

  // Load initial data
  useEffect(() => {
    let mounted = true;

    async function loadInitial() {
      try {
        const [st, acts] = await Promise.all([
          getMonitorStatus(),
          getMonitorActivities("", 200),
        ]);
        if (!mounted) return;
        setStatus(st);
        setActivities(acts);
        setBridgeOnline(true);
      } catch {
        if (!mounted) return;
        setBridgeOnline(false);
      }
    }

    loadInitial();

    // Poll status every 5s
    const interval = setInterval(async () => {
      try {
        const st = await getMonitorStatus();
        if (mounted) {
          setStatus(st);
          setBridgeOnline(true);
        }
      } catch {
        if (mounted) setBridgeOnline(false);
      }
    }, 5000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // SSE real-time stream
  useEffect(() => {
    if (bridgeOnline === false) return;

    const disconnect = connectMonitorStream(
      (activity) => {
        setActivities((prev) => {
          const next = [...prev, activity];
          // Keep max 500 in UI
          return next.length > 500 ? next.slice(-500) : next;
        });
        setConnected(true);
      },
      () => {
        setConnected(false);
      },
    );
    disconnectRef.current = disconnect;

    return () => {
      disconnect();
      disconnectRef.current = null;
    };
  }, [bridgeOnline]);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [activities, autoScroll]);

  const filtered = activeFilter
    ? activities.filter((a) => a.category === activeFilter)
    : activities;

  const activeJobs = status?.active_jobs || [];

  // Offline state
  if (bridgeOnline === false) {
    return (
      <div className="flex flex-col items-center justify-center py-32">
        <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
          <WifiOff className="w-8 h-8 text-gray-400" />
        </div>
        <h2 className="text-lg font-semibold text-gray-700 mb-1">
          Chat Bridge chưa chạy
        </h2>
        <p className="text-[13px] text-gray-400 mb-4">
          Khởi động chat bridge để xem monitor
        </p>
        <code className="text-[12px] text-indigo-600 font-mono bg-indigo-50 px-4 py-2 rounded-lg">
          cd ~/Youtube/video-factory && python3 chat_bridge.py
        </code>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 tracking-tight">
            Monitor
          </h1>
          <p className="text-[13px] text-gray-400 mt-1">
            Theo dõi hoạt động Chat Bridge real-time
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Connection status */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-medium ${
              connected
                ? "bg-emerald-50 text-emerald-600"
                : "bg-gray-50 text-gray-400"
            }`}
          >
            {connected ? (
              <Wifi className="w-3.5 h-3.5" />
            ) : (
              <WifiOff className="w-3.5 h-3.5" />
            )}
            {connected ? "Real-time" : "Đang kết nối..."}
          </div>
          {/* Clear */}
          <button
            onClick={() => setActivities([])}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-lg bg-gray-50 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Xóa log
          </button>
        </div>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Server */}
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-emerald-500" />
            </div>
            <span className="text-[12px] font-medium text-gray-400">
              Server
            </span>
          </div>
          <p className="text-[15px] font-semibold text-gray-800">
            {status?.server === "running" ? "Hoạt động" : "---"}
          </p>
          <p className="text-[11px] text-gray-400 mt-0.5">
            SDK Pool:{" "}
            {status?.sdk_pool ? (
              <span className="text-emerald-500">
                {status.sdk_pool.available}/{status.sdk_pool.pool_size} sẵn sàng
              </span>
            ) : (
              <span className="text-gray-400">---</span>
            )}
          </p>
        </div>

        {/* SDK Pool */}
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-blue-500" />
            </div>
            <span className="text-[12px] font-medium text-gray-400">
              SDK Pool
            </span>
          </div>
          <p className="text-[15px] font-semibold text-gray-800">
            {status?.sdk_pool?.in_use ?? 0} / {status?.sdk_pool?.total_created ?? 0}
          </p>
          <p className="text-[11px] text-gray-400 mt-0.5">
            đang dùng / đã tạo
          </p>
        </div>

        {/* Active jobs */}
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
              <Loader2
                className={`w-4 h-4 text-purple-500 ${activeJobs.length > 0 ? "animate-spin" : ""}`}
              />
            </div>
            <span className="text-[12px] font-medium text-gray-400">
              Jobs
            </span>
          </div>
          <p className="text-[15px] font-semibold text-gray-800">
            {activeJobs.length}
          </p>
          <p className="text-[11px] text-gray-400 mt-0.5">
            đang chạy
          </p>
        </div>

        {/* Total activities */}
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
              <Activity className="w-4 h-4 text-amber-500" />
            </div>
            <span className="text-[12px] font-medium text-gray-400">
              Activities
            </span>
          </div>
          <p className="text-[15px] font-semibold text-gray-800">
            {status?.total_activities ?? 0}
          </p>
          <p className="text-[11px] text-gray-400 mt-0.5">
            tổng sự kiện
          </p>
        </div>
      </div>

      {/* Active jobs detail */}
      {activeJobs.length > 0 && (
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-[13px] font-semibold text-gray-700 mb-3">
            Jobs đang chạy
          </h3>
          <div className="space-y-3">
            {activeJobs.map((job) => (
              <JobCard key={job.job_id} job={job} />
            ))}
          </div>
        </div>
      )}

      {/* Activity log */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {/* Filter tabs */}
        <div className="flex items-center gap-1 px-4 pt-4 pb-2 border-b border-gray-50">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeFilter === cat.key;
            const count = cat.key
              ? activities.filter((a) => a.category === cat.key).length
              : activities.length;
            return (
              <button
                key={cat.key}
                onClick={() => setActiveFilter(cat.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-600"
                    : "text-gray-400 hover:bg-gray-50 hover:text-gray-600"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {cat.label}
                {count > 0 && (
                  <span
                    className={`ml-0.5 text-[10px] px-1.5 py-0.5 rounded-full ${
                      isActive
                        ? "bg-indigo-100 text-indigo-600"
                        : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
          <div className="flex-1" />
          <label className="flex items-center gap-1.5 text-[11px] text-gray-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded border-gray-300 text-indigo-500 focus:ring-indigo-500 w-3.5 h-3.5"
            />
            Auto-scroll
          </label>
        </div>

        {/* Log entries */}
        <div className="max-h-[500px] overflow-y-auto px-4 py-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <Activity className="w-8 h-8 mb-2 opacity-30" />
              <p className="text-[13px]">Chưa có hoạt động nào</p>
              <p className="text-[11px] mt-1">
                Sử dụng chat hoặc generate prompt để xem log ở đây
              </p>
            </div>
          ) : (
            filtered.map((entry) => (
              <ActivityRow key={entry.id} entry={entry} />
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>

      {/* SDK Pool detail */}
      {status?.sdk_pool && status.sdk_pool.total_created > 0 && (
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-[13px] font-semibold text-gray-700 mb-3">
            SDK Warm Pool
          </h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="px-3 py-2 bg-gray-50 rounded-lg text-center">
              <p className="text-[18px] font-bold text-gray-700">{status.sdk_pool.pool_size}</p>
              <p className="text-[10px] text-gray-400">Max pool</p>
            </div>
            <div className="px-3 py-2 bg-emerald-50 rounded-lg text-center">
              <p className="text-[18px] font-bold text-emerald-600">{status.sdk_pool.total_created}</p>
              <p className="text-[10px] text-gray-400">Đã tạo</p>
            </div>
            <div className="px-3 py-2 bg-blue-50 rounded-lg text-center">
              <p className="text-[18px] font-bold text-blue-600">{status.sdk_pool.available}</p>
              <p className="text-[10px] text-gray-400">Sẵn sàng</p>
            </div>
            <div className="px-3 py-2 bg-amber-50 rounded-lg text-center">
              <p className="text-[18px] font-bold text-amber-600">{status.sdk_pool.in_use}</p>
              <p className="text-[10px] text-gray-400">Đang dùng</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const ACTION_LABELS: Record<string, { label: string; icon?: typeof Brain }> = {
  thinking: { label: "Suy nghĩ", icon: Brain },
  thought_done: { label: "Suy nghĩ xong", icon: Brain },
  writing: { label: "Đang viết", icon: Pen },
  stream_start: { label: "Bắt đầu" },
  stream_done: { label: "Hoàn thành" },
  send_message: { label: "Gửi tin nhắn" },
  response: { label: "Phản hồi" },
  generate: { label: "Tạo" },
  plan_done: { label: "Kế hoạch xong" },
  scene_prompt: { label: "Prompt cảnh" },
  extract: { label: "Trích xuất" },
  finalize: { label: "Chốt" },
};

function ActivityRow({ entry }: { entry: MonitorActivity }) {
  const meta = categoryMeta(entry.category);
  const Icon = meta.icon;
  const actionInfo = ACTION_LABELS[entry.action];
  const isThinking = entry.action === "thinking" || entry.action === "thought_done";
  const isWriting = entry.action === "writing";

  // Thinking rows get a special style
  if (isThinking) {
    return (
      <div
        className={`flex items-start gap-3 px-3 py-1.5 rounded-lg border transition-colors ${
          entry.action === "thinking"
            ? "bg-violet-50/60 border-violet-100"
            : "bg-violet-50/30 border-violet-50"
        }`}
      >
        <div className="mt-0.5">
          {entry.action === "thinking" ? (
            <Brain className="w-3.5 h-3.5 text-violet-500 animate-pulse" />
          ) : (
            <Brain className="w-3.5 h-3.5 text-violet-400" />
          )}
        </div>
        <div
          className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-violet-100 text-violet-600 shrink-0`}
        >
          <Brain className="w-3 h-3" />
          {actionInfo?.label || entry.action}
        </div>
        <span className="text-[11px] text-violet-500/80 truncate flex-1 italic">
          {entry.detail}
        </span>
        {entry.project_id && (
          <span className="text-[10px] text-gray-400 font-mono shrink-0">
            {entry.project_id}
            {entry.video_id && `/${entry.video_id.slice(0, 12)}`}
          </span>
        )}
        <span className="text-[10px] text-gray-400 shrink-0 w-16 text-right">
          {formatTime(entry.timestamp)}
        </span>
      </div>
    );
  }

  // Writing rows
  if (isWriting) {
    return (
      <div className="flex items-start gap-3 px-3 py-1.5 rounded-lg border bg-sky-50/50 border-sky-100 transition-colors">
        <div className="mt-0.5">
          <Pen className="w-3.5 h-3.5 text-sky-500 animate-pulse" />
        </div>
        <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-100 text-sky-600 shrink-0">
          <Pen className="w-3 h-3" />
          Đang viết
        </div>
        <span className="text-[11px] text-sky-500/80 truncate flex-1">
          {entry.detail}
        </span>
        {entry.project_id && (
          <span className="text-[10px] text-gray-400 font-mono shrink-0">
            {entry.project_id}
            {entry.video_id && `/${entry.video_id.slice(0, 12)}`}
          </span>
        )}
        <span className="text-[10px] text-gray-400 shrink-0 w-16 text-right">
          {formatTime(entry.timestamp)}
        </span>
      </div>
    );
  }

  // Default row
  return (
    <div
      className={`flex items-start gap-3 px-3 py-2 rounded-lg border transition-colors ${statusColor(entry.status)}`}
    >
      <div className="mt-0.5">{statusIcon(entry.status)}</div>
      <div
        className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${meta.bg} ${meta.color} shrink-0`}
      >
        <Icon className="w-3 h-3" />
        {meta.label}
      </div>
      <span className="text-[12px] font-medium text-gray-600 shrink-0">
        {actionInfo?.label || entry.action}
      </span>
      <span className="text-[12px] text-gray-500 truncate flex-1">
        {entry.detail}
      </span>
      {entry.project_id && (
        <span className="text-[10px] text-gray-400 font-mono shrink-0">
          {entry.project_id}
          {entry.video_id && `/${entry.video_id.slice(0, 12)}`}
        </span>
      )}
      <span className="text-[10px] text-gray-400 shrink-0 w-16 text-right">
        {formatTime(entry.timestamp)}
      </span>
    </div>
  );
}

function JobCard({ job }: { job: MonitorJob }) {
  const progress =
    job.total > 0 ? Math.round((job.completed / job.total) * 100) : 0;

  return (
    <div className="flex items-center gap-4 px-4 py-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
      <Loader2 className="w-5 h-5 text-indigo-500 animate-spin shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[13px] font-semibold text-gray-700">
            {job.action}
          </span>
          <span className="text-[11px] text-gray-400">
            {job.project_id}/{job.video_id}
          </span>
        </div>
        {job.total > 0 && (
          <div className="flex items-center gap-3">
            <div className="flex-1 h-1.5 bg-indigo-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-[11px] font-medium text-indigo-600 shrink-0">
              {job.completed}/{job.total}
            </span>
          </div>
        )}
      </div>
      <span className="text-[10px] text-gray-400 shrink-0">
        {timeAgo(job.started_at)}
      </span>
    </div>
  );
}
