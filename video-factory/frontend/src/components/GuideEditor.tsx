"use client";

import { useState } from "react";
import { Pencil, Save, X, Loader2 } from "lucide-react";

interface GuideEditorProps {
  content: string;
  exists: boolean;
  updatedAt: string | null;
  onSave: (content: string) => Promise<void>;
  placeholder: string;
  emptyMessage: string;
}

export function GuideEditor({ content, exists, updatedAt, onSave, placeholder, emptyMessage }: GuideEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(content);
  const [isSaving, setIsSaving] = useState(false);

  const handleEdit = () => { setEditContent(content); setIsEditing(true); };
  const handleCancel = () => { setEditContent(content); setIsEditing(false); };
  const handleSave = async () => { setIsSaving(true); try { await onSave(editContent); setIsEditing(false); } finally { setIsSaving(false); } };

  if (isEditing) {
    return (
      <div className="space-y-3">
        <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} placeholder={placeholder}
          className="w-full bg-white border border-gray-200 rounded-xl p-4 text-[13px] text-gray-700 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 resize-y transition-all"
          style={{ minHeight: "400px" }} />
        <div className="flex items-center gap-2 justify-end">
          <button onClick={handleCancel} disabled={isSaving} className="flex items-center gap-2 px-4 py-2 text-[13px] text-gray-400 hover:text-gray-600 rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-40">
            <X className="w-4 h-4" /> Hủy
          </button>
          <button onClick={handleSave} disabled={isSaving} className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold bg-indigo-500 text-white rounded-xl hover:bg-indigo-600 transition-colors disabled:opacity-60 shadow-sm">
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Lưu
          </button>
        </div>
      </div>
    );
  }

  if (!exists || !content) {
    return (
      <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl p-8 text-center">
        <p className="text-[13px] text-gray-400 mb-4">{emptyMessage}</p>
        <button onClick={handleEdit} className="inline-flex items-center gap-2 px-4 py-2 text-[13px] font-semibold bg-indigo-500 text-white rounded-xl hover:bg-indigo-600 transition-colors shadow-sm">
          <Pencil className="w-4 h-4" /> Tạo mới
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-4">
        <pre className="flex-1 bg-white border border-gray-100 rounded-xl p-4 text-[13px] text-gray-600 whitespace-pre-wrap font-mono overflow-auto">{content}</pre>
        <button onClick={handleEdit} className="flex-shrink-0 flex items-center gap-2 px-3 py-2 text-[13px] text-gray-400 hover:text-indigo-500 rounded-xl hover:bg-indigo-50 border border-gray-200 transition-colors">
          <Pencil className="w-4 h-4" /> Sửa
        </button>
      </div>
      {updatedAt && <p className="text-[11px] text-gray-400">Cập nhật lần cuối: {new Date(updatedAt).toLocaleString("vi-VN")}</p>}
    </div>
  );
}
