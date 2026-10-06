"use client";

import { useState } from "react";
import { Check, RotateCcw, Loader2, Image, Video, Play, Eye, Clock, X, Sparkles } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import type { Scene } from "@/lib/api";

interface SceneTimelineProps {
  scenes: Scene[];
  projectId: string;
  videoId: string;
  onApprove: (sceneNumber: number) => void;
  onRedo: (sceneNumber: number) => void;
  onClickScene: (scene: Scene) => void;
  onGeneratePrompt?: (sceneNumber: number) => void;
  promptingScenes?: Set<number>;
}

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function SceneCell({
  scene,
  onApprove,
  onRedo,
  onClick,
  onGeneratePrompt,
  isPrompting,
}: {
  scene: Scene;
  onApprove: (n: number) => void;
  onRedo: (n: number) => void;
  onClick: () => void;
  onGeneratePrompt?: (n: number) => void;
  isPrompting?: boolean;
}) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const duration = scene.timestamp_end - scene.timestamp_start;
  const hasAsset = !!scene.asset_url;

  const statusColor = {
    pending: "border-gray-200",
    generating: "border-indigo-300 animate-pulse",
    review: "border-amber-300",
    approved: "border-emerald-300",
    redo: "border-rose-300",
  }[scene.status] || "border-gray-200";

  return (
    <>
      <div className={`bg-white rounded-xl border-2 ${statusColor} overflow-hidden hover:shadow-md transition-all`}>
        {/* Preview area */}
        <div
          className="aspect-video bg-gray-50 relative cursor-pointer group"
          onClick={() => hasAsset ? setPreviewOpen(true) : onClick()}
        >
          {hasAsset ? (
            <>
              <img src={scene.asset_url} alt={`Cảnh ${scene.scene_number}`} className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-center justify-center">
                <Eye className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </>
          ) : scene.status === "generating" ? (
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
              <span className="text-[10px] text-gray-400">Đang tạo...</span>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-1.5 text-gray-300">
              {scene.visual_type === "video" ? <Video className="w-6 h-6" /> : <Image className="w-6 h-6" />}
              <span className="text-[10px] text-gray-400">{scene.visual_type === "video" ? "Video" : "Ảnh"}</span>
            </div>
          )}

          {/* Scene number badge */}
          <div className="absolute top-2 left-2 bg-black/60 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
            #{scene.scene_number}
          </div>

          {/* Duration badge */}
          <div className="absolute top-2 right-2 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" />
            {duration.toFixed(0)}s
          </div>

          {/* Type + Content tag */}
          <div className="absolute bottom-2 left-2 flex items-center gap-1">
            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${scene.visual_type === "video" ? "bg-purple-500/90 text-white" : "bg-sky-500/90 text-white"}`}>
              {scene.visual_type === "video" ? "Video" : "Ảnh"}
            </span>
            {scene.content_tag && (
              <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-white/80 text-gray-600 backdrop-blur-sm">
                {scene.content_tag}
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-gray-400">
              {formatTime(scene.timestamp_start)} — {formatTime(scene.timestamp_end)}
            </span>
            <StatusBadge status={scene.status} />
          </div>

          <p className="text-[11px] text-gray-600 leading-relaxed line-clamp-3 min-h-[40px]">
            {scene.script_text || scene.veo3_prompt || "—"}
          </p>

          {/* Prompt status */}
          {scene.veo3_prompt ? (
            <p className="text-[10px] text-indigo-500 mt-1.5 line-clamp-2 italic">{scene.veo3_prompt.slice(0, 80)}...</p>
          ) : (
            <p className="text-[10px] text-gray-300 mt-1.5 italic">Chưa có prompt</p>
          )}

          {/* Actions */}
          <div className="flex items-center gap-1.5 mt-2.5 pt-2.5 border-t border-gray-100">
            {onGeneratePrompt && (
              <button
                onClick={(e) => { e.stopPropagation(); onGeneratePrompt(scene.scene_number); }}
                disabled={isPrompting}
                className="flex-1 flex items-center justify-center gap-1 py-1.5 text-[10px] font-semibold rounded-lg bg-purple-50 text-purple-600 hover:bg-purple-100 disabled:opacity-50 transition-colors"
              >
                {isPrompting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                {isPrompting ? "Đang tạo..." : scene.veo3_prompt ? "Tạo lại prompt" : "Tạo prompt"}
              </button>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); onApprove(scene.scene_number); }}
              disabled={scene.status === "approved"}
              className="flex-1 flex items-center justify-center gap-1 py-1.5 text-[10px] font-semibold rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <Check className="w-3 h-3" /> Duyệt
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onRedo(scene.scene_number); }}
              className="flex-1 flex items-center justify-center gap-1 py-1.5 text-[10px] font-semibold rounded-lg bg-amber-50 text-amber-600 hover:bg-amber-100 transition-colors"
            >
              <RotateCcw className="w-3 h-3" /> Tạo lại
            </button>
            <button
              onClick={onClick}
              className="py-1.5 px-2 text-[10px] font-semibold rounded-lg bg-gray-50 text-gray-500 hover:bg-gray-100 transition-colors"
            >
              <Eye className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      {previewOpen && hasAsset && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setPreviewOpen(false)}>
          <div className="relative max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setPreviewOpen(false)} className="absolute -top-10 right-0 text-white/80 hover:text-white">
              <X className="w-6 h-6" />
            </button>
            <img src={scene.asset_url} alt={`Cảnh ${scene.scene_number}`} className="w-full rounded-xl shadow-2xl" />
            <div className="bg-black/80 rounded-b-xl px-4 py-3 -mt-1">
              <p className="text-[12px] text-white/70">Cảnh {scene.scene_number} · {formatTime(scene.timestamp_start)} — {formatTime(scene.timestamp_end)}</p>
              <p className="text-[13px] text-white mt-1">{scene.script_text || scene.veo3_prompt}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function SceneTimeline({ scenes, projectId, videoId, onApprove, onRedo, onClickScene, onGeneratePrompt, promptingScenes }: SceneTimelineProps) {
  const approved = scenes.filter((s) => s.status === "approved").length;
  const total = scenes.length;
  const progress = total > 0 ? (approved / total) * 100 : 0;

  return (
    <div>
      {/* Progress bar */}
      <div className="bg-white rounded-xl p-4 mb-4 border border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[12px] font-semibold text-gray-600">Tiến độ</span>
          <span className="text-[12px] text-gray-400">{approved}/{total} cảnh đã duyệt</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Scene grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        {scenes.map((scene) => (
          <SceneCell
            key={scene.scene_number}
            scene={scene}
            onApprove={onApprove}
            onRedo={onRedo}
            onClick={() => onClickScene(scene)}
            onGeneratePrompt={onGeneratePrompt}
            isPrompting={promptingScenes?.has(scene.scene_number)}
          />
        ))}
      </div>
    </div>
  );
}
