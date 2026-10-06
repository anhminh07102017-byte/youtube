"use client";

import { useState } from "react";
import { X, Plus, Loader2, Link as LinkIcon } from "lucide-react";
import type { CreateProjectData } from "@/lib/api";

interface CreateProjectModalProps {
  onClose: () => void;
  onSubmit: (data: CreateProjectData) => Promise<void>;
}

function generateId(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "d")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 50);
}

export function CreateProjectModal({ onClose, onSubmit }: CreateProjectModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<CreateProjectData>({
    id: "",
    name: "",
    sources: [],
    notes: "",
  });
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceTitle, setSourceTitle] = useState("");

  const handleNameChange = (name: string) => {
    setFormData((prev) => ({ ...prev, name, id: generateId(name) }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      onClose();
    } catch (err: any) {
      if (err?.message?.includes("409") || err?.message?.includes("exist")) {
        const suffix = Math.random().toString(36).slice(2, 6);
        try { await onSubmit({ ...formData, id: `${formData.id}-${suffix}` }); onClose(); } catch {}
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const addSource = () => {
    if (sourceUrl.trim()) {
      const entry = sourceTitle.trim() ? `${sourceTitle.trim()}|||${sourceUrl.trim()}` : sourceUrl.trim();
      setFormData((prev) => ({ ...prev, sources: [...prev.sources, entry] }));
      setSourceUrl("");
      setSourceTitle("");
    }
  };

  const removeSource = (index: number) => {
    setFormData((prev) => ({ ...prev, sources: prev.sources.filter((_, i) => i !== index) }));
  };

  const parseSource = (source: string) => {
    if (source.includes("|||")) { const [title, url] = source.split("|||"); return { title, url }; }
    return { title: source, url: source.startsWith("http") ? source : "" };
  };

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <h2 className="text-[17px] font-bold text-gray-800">Tạo dự án</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-[13px] font-semibold text-gray-600 mb-1.5">Tên dự án</label>
            <input type="text" required placeholder="VD: Việt Nam chống Pháp" value={formData.name}
              onChange={(e) => handleNameChange(e.target.value)}
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-[13px] text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 transition-all" />
            {formData.id && <p className="mt-1 text-[11px] text-gray-400">Mã: {formData.id}</p>}
          </div>

          <div>
            <label className="block text-[13px] font-semibold text-gray-600 mb-1.5">Nguồn tham khảo</label>
            <p className="text-[11px] text-gray-400 mb-2">Gắn link YouTube, bài viết lịch sử, tài liệu tham khảo</p>
            <div className="space-y-2 mb-2">
              <input type="text" placeholder="Tiêu đề" value={sourceTitle} onChange={(e) => setSourceTitle(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-[13px] text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 transition-all" />
              <div className="flex gap-2">
                <input type="text" placeholder="Dán link..." value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSource(); } }}
                  className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-[13px] text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 transition-all" />
                <button type="button" onClick={addSource} className="p-2.5 bg-indigo-50 rounded-xl hover:bg-indigo-100 text-indigo-500 transition-colors">
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>
            {formData.sources.length > 0 && (
              <div className="space-y-1.5">
                {formData.sources.map((source, i) => {
                  const parsed = parseSource(source);
                  return (
                    <div key={i} className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2 group">
                      <LinkIcon className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] text-gray-700 truncate">{parsed.title}</p>
                        {parsed.url && parsed.url !== parsed.title && <p className="text-[11px] text-gray-400 truncate">{parsed.url}</p>}
                      </div>
                      <button type="button" onClick={() => removeSource(i)} className="opacity-0 group-hover:opacity-100 hover:text-rose-500 text-gray-400 transition-all">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div>
            <label className="block text-[13px] font-semibold text-gray-600 mb-1.5">Ghi chú</label>
            <textarea placeholder="Mô tả dự án..." value={formData.notes}
              onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))} rows={3}
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-[13px] text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 resize-y transition-all" />
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2.5 text-[13px] font-semibold rounded-xl border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors">Hủy</button>
            <button type="submit" disabled={isSubmitting || !formData.id || !formData.name}
              className="flex-1 px-4 py-2.5 text-[13px] font-semibold rounded-xl bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm flex items-center justify-center gap-2">
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {isSubmitting ? "Đang tạo..." : "Tạo dự án"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
