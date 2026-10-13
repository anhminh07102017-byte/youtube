"use client";

import { Image, Video, Check, RotateCcw } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { assetUrl } from "@/lib/api";
import type { Scene } from "@/lib/api";

interface SceneCardProps {
  scene: Scene;
  onApprove?: (sceneNumber: number) => void;
  onRedo?: (sceneNumber: number) => void;
  onClick?: (scene: Scene) => void;
}

export function SceneCard({ scene, onApprove, onRedo, onClick }: SceneCardProps) {
  const TypeIcon = scene.visual_type === "video" ? Video : Image;
  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  return (
    <div className="bg-white rounded-2xl overflow-hidden hover:shadow-md transition-all group cursor-pointer border border-transparent hover:border-gray-100"
      onClick={() => onClick?.(scene)}>
      <div className="aspect-video bg-gray-50 relative flex items-center justify-center">
        {scene.asset_url ? (
          <img src={assetUrl(scene.asset_url)} alt={`Cảnh ${scene.scene_number}`} className="w-full h-full object-cover" />
        ) : (
          <div className="text-gray-300 flex flex-col items-center gap-2">
            <TypeIcon className="w-8 h-8" />
            <span className="text-[11px] text-gray-400">Chưa có tài nguyên</span>
          </div>
        )}
        <div className="absolute top-2 left-2 bg-black/40 backdrop-blur-sm text-white text-[11px] px-2 py-1 rounded-lg font-semibold">Cảnh {scene.scene_number}</div>
        {scene.veo3_prompt && (
          <div className="absolute top-2 right-2">
            <span className={`text-[11px] px-2 py-1 rounded-lg font-semibold backdrop-blur-sm ${scene.visual_type === "video" ? "bg-purple-500/90 text-white" : "bg-blue-500/90 text-white"}`}>
              {scene.visual_type === "video" ? "Video" : "Ảnh"}
            </span>
          </div>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] text-gray-400">{formatTime(scene.timestamp_start)} - {formatTime(scene.timestamp_end)}</span>
          <StatusBadge status={scene.status} />
        </div>
        <p className="text-[13px] text-gray-600 line-clamp-2 mb-3">{scene.veo3_prompt || scene.script_text || ""}</p>
        <div className="flex gap-2">
          <button onClick={(e) => { e.stopPropagation(); onApprove?.(scene.scene_number); }} disabled={scene.status === "approved"}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
            <Check className="w-3.5 h-3.5" /> Duyệt
          </button>
          <button onClick={(e) => { e.stopPropagation(); onRedo?.(scene.scene_number); }}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-amber-50 text-amber-600 hover:bg-amber-100 transition-colors">
            <RotateCcw className="w-3.5 h-3.5" /> Làm lại
          </button>
        </div>
      </div>
    </div>
  );
}
