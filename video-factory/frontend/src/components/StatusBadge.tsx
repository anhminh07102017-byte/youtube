"use client";

const statusStyles: Record<string, string> = {
  draft: "bg-gray-50 text-gray-500",
  script_ready: "bg-blue-50 text-blue-600",
  audio_ready: "bg-purple-50 text-purple-600",
  shotlist_ready: "bg-cyan-50 text-cyan-600",
  assets_generating: "bg-indigo-50 text-indigo-600",
  assets_review: "bg-amber-50 text-amber-600",
  capcut_ready: "bg-emerald-50 text-emerald-600",
  done: "bg-emerald-50 text-emerald-600",
  approved: "bg-emerald-50 text-emerald-600",
  pending: "bg-gray-50 text-gray-500",
  generating: "bg-indigo-50 text-indigo-600",
  review: "bg-amber-50 text-amber-600",
  redo: "bg-orange-50 text-orange-600",
  rejected: "bg-rose-50 text-rose-600",
  error: "bg-rose-50 text-rose-600",
};

const statusLabels: Record<string, string> = {
  draft: "Nháp",
  script_ready: "Kịch bản xong",
  audio_ready: "Âm thanh xong",
  shotlist_ready: "Danh sách cảnh xong",
  assets_generating: "Đang tạo tài nguyên",
  assets_review: "Đang duyệt",
  capcut_ready: "CapCut xong",
  done: "Hoàn thành",
  approved: "Đã duyệt",
  pending: "Chờ xử lý",
  generating: "Đang tạo",
  review: "Đang duyệt",
  rejected: "Từ chối",
  redo: "Làm lại",
  error: "Lỗi",
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const style = statusStyles[status] || statusStyles.draft;
  const label = statusLabels[status] || (status ? status.replace(/_/g, " ") : "Nháp");

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[11px] font-semibold ${style} ${className}`}
    >
      {label}
    </span>
  );
}
