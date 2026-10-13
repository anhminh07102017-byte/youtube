"use client";

import { useState, useRef } from "react";
import { Check, RotateCcw, Loader2, Image, Video, Eye, Clock, X, Sparkles, Merge, Trash2, CheckSquare, Square, Upload } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { assetUrl, mergeScenes, batchClearPrompts, batchClearAssets } from "@/lib/api";
import type { Scene } from "@/lib/api";

interface SceneTimelineProps {
  scenes: Scene[];
  projectId: string;
  videoId: string;
  onApprove: (sceneNumber: number) => void;
  onRedo: (sceneNumber: number) => void;
  onUpload?: (sceneNumber: number, file: File) => void;
  onClickScene: (scene: Scene) => void;
  onGeneratePrompt?: (sceneNumber: number) => void;
  promptingScenes?: Set<number>;
  onScenesUpdated?: () => void;
  onGenerateAssets?: (sceneNumbers: number[], visualTypeFilter?: 'image' | 'video') => void;
  generatingAssets?: boolean;
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
  onUpload,
  onClick,
  onGeneratePrompt,
  isPrompting,
  selected,
  selectMode,
  onToggleSelect,
}: {
  scene: Scene;
  onApprove: (n: number) => void;
  onRedo: (n: number) => void;
  onUpload?: (n: number, file: File) => void;
  onClick: () => void;
  onGeneratePrompt?: (n: number) => void;
  isPrompting?: boolean;
  selected: boolean;
  selectMode: boolean;
  onToggleSelect: (n: number) => void;
}) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const duration = scene.timestamp_end - scene.timestamp_start;
  const hasAsset = !!scene.asset_url;

  const statusColor = selected
    ? "border-indigo-500 ring-2 ring-indigo-200"
    : {
        pending: "border-gray-200",
        generating: "border-indigo-300 animate-pulse",
        review: "border-amber-300",
        approved: "border-emerald-300",
        redo: "border-rose-300",
      }[scene.status] || "border-gray-200";

  return (
    <>
      <div className={`bg-white rounded-xl border-2 ${statusColor} overflow-hidden hover:shadow-md transition-all relative group/card`}>
        {/* Checkbox */}
        <button
          onClick={(e) => { e.stopPropagation(); onToggleSelect(scene.scene_number); }}
          className={`absolute top-2 left-2 z-10 w-6 h-6 rounded-md flex items-center justify-center transition-all shadow-sm ${
            selected
              ? "bg-indigo-500 text-white border-2 border-indigo-600"
              : selectMode
                ? "bg-white text-gray-400 hover:text-indigo-500 border-2 border-gray-400 hover:border-indigo-400"
                : "bg-white/90 text-gray-400 border-2 border-gray-300"
          }`}
        >
          {selected ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : null}
        </button>

        {/* Preview area */}
        <div
          className="aspect-video bg-gray-50 relative cursor-pointer group"
          onClick={() => selectMode ? onToggleSelect(scene.scene_number) : hasAsset ? setPreviewOpen(true) : onClick()}
        >
          {hasAsset ? (
            <>
              {scene.visual_type === "video" ? (
                <video src={assetUrl(scene.asset_url)} className="w-full h-full object-cover" muted preload="metadata" />
              ) : (
                <img src={assetUrl(scene.asset_url)} alt={`Cảnh ${scene.scene_number}`} className="w-full h-full object-cover" />
              )}
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
              <Image className="w-6 h-6" />
              <span className="text-[10px] text-gray-400">Chưa có tài nguyên</span>
            </div>
          )}

          {/* Scene number badge */}
          <div className="absolute top-2 left-8 bg-black/60 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
            #{scene.scene_number}
          </div>

          {/* Duration badge */}
          <div className="absolute top-2 right-2 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" />
            {duration.toFixed(0)}s
          </div>

          {/* Type + Content tag — chỉ hiện khi đã có prompt */}
          {scene.veo3_prompt && (
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
          )}
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

          {/* Nhân vật */}
          {scene.flow_characters && scene.flow_characters.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {scene.flow_characters.map((name: string) => (
                <span key={name} className="text-[9px] px-1.5 py-0.5 rounded bg-violet-50 text-violet-600 font-medium">@{name}</span>
              ))}
            </div>
          )}

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
              onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
              className="py-1.5 px-2 text-[10px] font-semibold rounded-lg bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors"
              title="Upload ảnh/video"
            >
              <Upload className="w-3 h-3" />
            </button>
            <input ref={fileInputRef} type="file" accept="image/*,video/*" className="hidden"
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload?.(scene.scene_number, f); e.target.value = ""; }} />
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
            {scene.visual_type === "video" ? (
              <video src={assetUrl(scene.asset_url)} className="w-full rounded-xl shadow-2xl" controls autoPlay muted />
            ) : (
              <img src={assetUrl(scene.asset_url)} alt={`Cảnh ${scene.scene_number}`} className="w-full rounded-xl shadow-2xl" />
            )}
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

function isConsecutive(nums: number[]): boolean {
  const sorted = [...nums].sort((a, b) => a - b);
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) return false;
  }
  return true;
}

export function SceneTimeline({ scenes, projectId, videoId, onApprove, onRedo, onUpload, onClickScene, onGeneratePrompt, promptingScenes, onScenesUpdated, onGenerateAssets, generatingAssets }: SceneTimelineProps) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [actionLoading, setActionLoading] = useState(false);

  const approved = scenes.filter((s) => s.status === "approved").length;
  const total = scenes.length;
  const progress = total > 0 ? (approved / total) * 100 : 0;
  const selectMode = selected.size > 0;

  const toggleSelect = (n: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === scenes.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(scenes.map((s) => s.scene_number)));
    }
  };

  const videoScenes = scenes.filter((s) => s.visual_type === "video");
  const imageScenes = scenes.filter((s) => s.visual_type === "image" || !s.visual_type);

  const selectAllVideos = () => {
    const videoNums = videoScenes.map((s) => s.scene_number);
    const allVideoSelected = videoScenes.length > 0 && videoScenes.every((s) => selected.has(s.scene_number));
    if (allVideoSelected) {
      setSelected((prev) => { const next = new Set(prev); videoNums.forEach((n) => next.delete(n)); return next; });
    } else {
      setSelected((prev) => { const next = new Set(prev); videoNums.forEach((n) => next.add(n)); return next; });
    }
  };

  const selectAllImages = () => {
    const imageNums = imageScenes.map((s) => s.scene_number);
    const allImageSelected = imageScenes.length > 0 && imageScenes.every((s) => selected.has(s.scene_number));
    if (allImageSelected) {
      setSelected((prev) => { const next = new Set(prev); imageNums.forEach((n) => next.delete(n)); return next; });
    } else {
      setSelected((prev) => { const next = new Set(prev); imageNums.forEach((n) => next.add(n)); return next; });
    }
  };

  const clearSelection = () => setSelected(new Set());

  const selectedNums = Array.from(selected).sort((a, b) => a - b);
  const canMerge = selected.size >= 2 && isConsecutive(selectedNums);
  const selectedWithPrompt = scenes.filter((s) => selected.has(s.scene_number) && s.veo3_prompt).length;
  const selectedWithAsset = scenes.filter((s) => selected.has(s.scene_number) && s.asset_path).length;

  const handleMerge = async () => {
    if (!confirm(`Gộp ${selected.size} phân đoạn (#${selectedNums[0]}–#${selectedNums[selectedNums.length - 1]}) thành 1? Prompt và asset sẽ bị xóa.`)) return;
    setActionLoading(true);
    try {
      await mergeScenes(projectId, videoId, selectedNums);
      clearSelection();
      onScenesUpdated?.();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Lỗi gộp phân đoạn");
    } finally {
      setActionLoading(false);
    }
  };

  const handleBatchClearPrompts = async () => {
    if (!confirm(`Xóa prompt của ${selectedWithPrompt} phân đoạn đã chọn?`)) return;
    setActionLoading(true);
    try {
      await batchClearPrompts(projectId, videoId, selectedNums);
      clearSelection();
      onScenesUpdated?.();
    } catch {
      alert("Lỗi xóa prompt");
    } finally {
      setActionLoading(false);
    }
  };

  const handleBatchClearAssets = async () => {
    if (!confirm(`Xóa ảnh/video của ${selectedWithAsset} phân đoạn đã chọn?`)) return;
    setActionLoading(true);
    try {
      await batchClearAssets(projectId, videoId, selectedNums);
      clearSelection();
      onScenesUpdated?.();
    } catch {
      alert("Lỗi xóa assets");
    } finally {
      setActionLoading(false);
    }
  };

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
            onUpload={onUpload}
            onClick={() => onClickScene(scene)}
            onGeneratePrompt={onGeneratePrompt}
            isPrompting={promptingScenes?.has(scene.scene_number)}
            selected={selected.has(scene.scene_number)}
            selectMode={selectMode}
            onToggleSelect={toggleSelect}
          />
        ))}
      </div>

      {/* Floating action bar */}
      {selectMode && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-white rounded-2xl shadow-2xl border border-gray-200 px-5 py-3 flex items-center gap-3 animate-in slide-in-from-bottom">
          {/* Selection info */}
          <div className="flex items-center gap-2 pr-3 border-r border-gray-200">
            <button onClick={selectAll} className="flex items-center gap-1.5 text-[12px] font-semibold text-gray-600 hover:text-indigo-600 transition-colors">
              {selected.size === scenes.length ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
              Tất cả
            </button>
            {imageScenes.length > 0 && (
              <button onClick={selectAllImages} className="flex items-center gap-1.5 text-[12px] font-semibold text-sky-600 hover:text-sky-700 transition-colors" title="Chọn/bỏ chọn tất cả ảnh">
                <Image className="w-3.5 h-3.5" />
                Ảnh ({imageScenes.length})
              </button>
            )}
            {videoScenes.length > 0 && (
              <button onClick={selectAllVideos} className="flex items-center gap-1.5 text-[12px] font-semibold text-purple-600 hover:text-purple-700 transition-colors" title="Chọn/bỏ chọn tất cả video">
                <Video className="w-3.5 h-3.5" />
                Video ({videoScenes.length})
              </button>
            )}
            <span className="text-[12px] font-bold text-indigo-600">{selected.size} đã chọn</span>
          </div>

          {/* Actions */}
          {canMerge && (
            <button
              onClick={handleMerge}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 transition-colors"
            >
              <Merge className="w-3.5 h-3.5" />
              Gộp ({selected.size})
            </button>
          )}

          {onGeneratePrompt && (
            <button
              onClick={() => { selectedNums.forEach((n) => onGeneratePrompt(n)); clearSelection(); }}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Tạo prompt ({selected.size})
            </button>
          )}

          {onGenerateAssets && selectedWithPrompt > 0 && (
            <>
              <button
                onClick={() => { onGenerateAssets(selectedNums, 'image'); clearSelection(); }}
                disabled={actionLoading || generatingAssets}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-teal-500 text-white hover:bg-teal-600 disabled:opacity-50 transition-colors"
              >
                <Image className="w-3.5 h-3.5" />
                Tạo ảnh
              </button>
              <button
                onClick={() => { onGenerateAssets(selectedNums, 'video'); clearSelection(); }}
                disabled={actionLoading || generatingAssets}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                <Video className="w-3.5 h-3.5" />
                Tạo video
              </button>
            </>
          )}

          {selectedWithPrompt > 0 && (
            <button
              onClick={handleBatchClearPrompts}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Xóa prompt ({selectedWithPrompt})
            </button>
          )}

          {selectedWithAsset > 0 && (
            <button
              onClick={handleBatchClearAssets}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Xóa ảnh/video ({selectedWithAsset})
            </button>
          )}

          {/* Close */}
          <button onClick={clearSelection} className="ml-1 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
