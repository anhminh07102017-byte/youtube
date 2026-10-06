"use client";

import { useState } from "react";
import { X, Check, RotateCcw, Image, Video } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import type { Scene } from "@/lib/api";

interface SceneDetailModalProps {
  scene: Scene;
  onClose: () => void;
  onApprove?: (sceneNumber: number) => void;
  onRedo?: (sceneNumber: number) => void;
  onUpdatePrompt?: (sceneNumber: number, prompt: string) => void;
}

export function SceneDetailModal({ scene, onClose, onApprove, onRedo, onUpdatePrompt }: SceneDetailModalProps) {
  const [editedPrompt, setEditedPrompt] = useState(scene.veo3_prompt);
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <h2 className="text-[17px] font-bold text-gray-800">Cảnh {scene.scene_number}</h2>
            <StatusBadge status={scene.status} />
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-6 space-y-6">
          <div className="aspect-video bg-gray-50 rounded-2xl overflow-hidden flex items-center justify-center">
            {scene.asset_url ? (
              <img src={scene.asset_url} alt={`Cảnh ${scene.scene_number}`} className="w-full h-full object-contain" />
            ) : (
              <div className="text-gray-300 flex flex-col items-center gap-2">
                {scene.visual_type === "video" ? <Video className="w-12 h-12" /> : <Image className="w-12 h-12" />}
                <span className="text-[13px] text-gray-400">Chưa có tài nguyên</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Loại", value: scene.visual_type === "video" ? "Video" : "Ảnh", bg: "bg-indigo-50", text: "text-indigo-600" },
              { label: "Thời gian", value: `${formatTime(scene.timestamp_start)} - ${formatTime(scene.timestamp_end)}`, bg: "bg-sky-50", text: "text-sky-600" },
              { label: "Thời lượng", value: `${Math.round(scene.timestamp_end - scene.timestamp_start)}s`, bg: "bg-violet-50", text: "text-violet-600" },
              { label: "Hiệu ứng", value: scene.effect || "Không có", bg: "bg-amber-50", text: "text-amber-600" },
            ].map((item) => (
              <div key={item.label} className={`${item.bg} rounded-xl p-3`}>
                <p className="text-[11px] text-gray-400 mb-0.5">{item.label}</p>
                <p className={`text-[13px] font-bold ${item.text}`}>{item.value}</p>
              </div>
            ))}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[13px] font-semibold text-gray-600">Prompt</p>
              {!isEditingPrompt && <button onClick={() => setIsEditingPrompt(true)} className="text-[12px] text-indigo-500 hover:text-indigo-700 font-medium">Sửa</button>}
            </div>
            {isEditingPrompt ? (
              <div className="space-y-2">
                <textarea value={editedPrompt} onChange={(e) => setEditedPrompt(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 resize-y min-h-[100px] transition-all" />
                <div className="flex gap-2 justify-end">
                  <button onClick={() => { setEditedPrompt(scene.veo3_prompt); setIsEditingPrompt(false); }} className="px-3 py-1.5 text-[12px] text-gray-400 hover:text-gray-600">Hủy</button>
                  <button onClick={() => { onUpdatePrompt?.(scene.scene_number, editedPrompt); setIsEditingPrompt(false); }}
                    className="px-3 py-1.5 text-[12px] bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 font-semibold transition-colors">Lưu prompt</button>
                </div>
              </div>
            ) : (
              <p className="text-[13px] text-gray-500 bg-gray-50 rounded-xl p-3">{scene.veo3_prompt}</p>
            )}
          </div>

          {scene.versions && scene.versions.length > 0 && (
            <div>
              <p className="text-[13px] font-semibold text-gray-600 mb-3">Lịch sử phiên bản</p>
              <div className="flex gap-3 overflow-x-auto pb-2">
                {scene.versions.map((v) => (
                  <div key={v.version} className="flex-shrink-0 w-32">
                    <div className="aspect-video bg-gray-50 rounded-xl overflow-hidden mb-1"><img src={v.asset_url} alt={`v${v.version}`} className="w-full h-full object-cover" /></div>
                    <p className="text-[11px] text-gray-400 text-center">v{v.version}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-4 border-t border-gray-100">
            <button onClick={() => onApprove?.(scene.scene_number)} disabled={scene.status === "approved"}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-[13px] font-semibold rounded-xl bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm">
              <Check className="w-4 h-4" /> Duyệt
            </button>
            <button onClick={() => onRedo?.(scene.scene_number)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-[13px] font-semibold rounded-xl bg-amber-500 text-white hover:bg-amber-600 transition-colors shadow-sm">
              <RotateCcw className="w-4 h-4" /> Đánh dấu làm lại
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
