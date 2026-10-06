"use client";

import { useState } from "react";
import { X, Loader2, Clock } from "lucide-react";
import type { CreateVideoData } from "@/lib/api";

interface CreateVideoModalProps {
  onClose: () => void;
  onSubmit: (data: CreateVideoData) => Promise<void>;
}

const DURATION_OPTIONS = [
  { value: 5, label: "5 phút", words: "750 – 900 từ", scenes: "10 – 15 cảnh" },
  { value: 8, label: "8 phút", words: "1.200 – 1.440 từ", scenes: "16 – 24 cảnh" },
  { value: 10, label: "10 phút", words: "1.500 – 1.800 từ", scenes: "20 – 30 cảnh" },
  { value: 15, label: "15 phút", words: "2.250 – 2.700 từ", scenes: "30 – 45 cảnh" },
  { value: 20, label: "20 phút", words: "3.000 – 3.600 từ", scenes: "40 – 60 cảnh" },
];

export function CreateVideoModal({ onClose, onSubmit }: CreateVideoModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [title, setTitle] = useState("");
  const [targetDuration, setTargetDuration] = useState(10);

  const selected = DURATION_OPTIONS.find((d) => d.value === targetDuration);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit({ id: "", title, target_duration: targetDuration });
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <h2 className="text-[17px] font-bold text-gray-800">Tạo video</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-[13px] font-semibold text-gray-600 mb-1.5">Tiêu đề</label>
            <input type="text" required placeholder="VD: Khởi nghĩa Hai Bà Trưng" value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-[13px] text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 transition-all" />
          </div>

          <div>
            <label className="block text-[13px] font-semibold text-gray-600 mb-2">Độ dài video</label>
            <div className="grid grid-cols-5 gap-1.5">
              {DURATION_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setTargetDuration(opt.value)}
                  className={`px-2 py-2.5 text-[12px] font-semibold rounded-lg border transition-all ${
                    targetDuration === opt.value
                      ? "bg-indigo-500 text-white border-indigo-500 shadow-sm"
                      : "bg-gray-50 text-gray-500 border-gray-200 hover:border-indigo-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            {selected && (
              <div className="mt-2.5 bg-indigo-50 rounded-lg px-3 py-2.5 flex items-start gap-2">
                <Clock className="w-3.5 h-3.5 text-indigo-500 mt-0.5 flex-shrink-0" />
                <div className="text-[11px] text-indigo-600">
                  <p>Kịch bản: <strong>{selected.words}</strong></p>
                  <p>Ước tính: <strong>{selected.scenes}</strong></p>
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2.5 text-[13px] font-semibold rounded-xl border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors">Hủy</button>
            <button type="submit" disabled={isSubmitting || !title.trim()}
              className="flex-1 px-4 py-2.5 text-[13px] font-semibold rounded-xl bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm flex items-center justify-center gap-2">
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {isSubmitting ? "Đang tạo..." : "Tạo video"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
