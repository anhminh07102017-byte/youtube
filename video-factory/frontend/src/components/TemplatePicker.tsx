"use client";

import { useState, useEffect } from "react";
import { Loader2, BookOpen, Check, Eye, ChevronDown, ChevronUp } from "lucide-react";
import { getTemplates, applyTemplateToVideo } from "@/lib/api";
import type { Template } from "@/lib/api";

interface TemplatePickerProps {
  projectId: string;
  videoId: string;
  targetGuide: "video_visual_guide" | "video_edit_guide";
  onApplied: () => void;
}

export function TemplatePicker({ projectId, videoId, targetGuide, onApplied }: TemplatePickerProps) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState<string | null>(null);
  const [applied, setApplied] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getTemplates();
        const all = [...data.image_styles, ...data.edit_styles];
        const filtered = all.filter((t) => t.applies_to.includes(targetGuide));
        setTemplates(filtered);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [targetGuide]);

  const handleApply = async (template: Template) => {
    setApplying(template.id);
    setApplied(null);
    setError(null);
    try {
      await applyTemplateToVideo(template.category, template.id, projectId, videoId, targetGuide);
      setApplied(template.id);
      onApplied();
    } catch (err) {
      setError(`Áp dụng thất bại: ${err instanceof Error ? err.message : "Lỗi không xác định"}`);
    } finally {
      setApplying(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-[12px] text-gray-400 py-3">
        <Loader2 className="w-4 h-4 animate-spin text-indigo-500" /> Đang tải kho tài nguyên...
      </div>
    );
  }

  if (templates.length === 0) return null;

  return (
    <div className="mb-5">
      <div className="flex items-center gap-2 mb-3">
        <BookOpen className="w-4 h-4 text-indigo-500" />
        <span className="text-[13px] font-semibold text-gray-600">Chọn từ kho tài nguyên</span>
      </div>
      {error && (
        <div className="mb-3 px-3 py-2 text-[11px] text-rose-600 bg-rose-50 rounded-lg">{error}</div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {templates.map((t) => (
          <div key={t.id} className="bg-white border border-gray-100 rounded-xl p-4 hover:border-indigo-200 transition-all">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <h4 className="text-[13px] font-bold text-gray-700 truncate">{t.name}</h4>
                <p className="text-[11px] text-gray-400 mt-0.5 line-clamp-2">{t.description}</p>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-500 hover:bg-indigo-50 transition-colors"
                  title="Xem chi tiết"
                >
                  {expanded === t.id ? <ChevronUp className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
                <button
                  onClick={() => handleApply(t)}
                  disabled={applying === t.id}
                  className="flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-semibold rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 transition-colors shadow-sm"
                >
                  {applying === t.id ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : applied === t.id ? (
                    <Check className="w-3 h-3" />
                  ) : null}
                  {applied === t.id ? "Đã áp dụng" : "Áp dụng"}
                </button>
              </div>
            </div>
            {expanded === t.id && (
              <div className="mt-3 bg-gray-50 rounded-lg p-3">
                <p className="text-[11px] text-gray-400 mb-1.5 font-semibold">Tóm tắt:</p>
                <p className="text-[12px] text-gray-500 whitespace-pre-line mb-3">{t.preview_summary}</p>
                <details className="group">
                  <summary className="text-[11px] text-indigo-500 font-semibold cursor-pointer hover:text-indigo-700">Xem nội dung đầy đủ</summary>
                  <pre className="mt-2 text-[11px] text-gray-500 font-mono whitespace-pre-wrap max-h-[200px] overflow-y-auto">{t.content}</pre>
                </details>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
