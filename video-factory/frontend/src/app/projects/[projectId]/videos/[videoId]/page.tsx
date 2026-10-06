"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  FileText,
  Music,
  List,
  Grid3X3,
  Download,
  Check,
  X,
  AlertCircle,
  CheckCircle2,
  Package,
  Palette,
  Scissors,
  MessageSquare,
  Mic,
} from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { GuideEditor } from "@/components/GuideEditor";
import { ChatPanel } from "@/components/ChatPanel";
import { SceneCard } from "@/components/SceneCard";
import { SceneDetailModal } from "@/components/SceneDetailModal";
import { SceneTimeline } from "@/components/SceneTimeline";
import { AudioUpload } from "@/components/AudioUpload";
import { TemplatePicker } from "@/components/TemplatePicker";
import { FlowLoginBanner } from "@/components/FlowLoginBanner";
import {
  getVideo,
  getScript,
  getScenes,
  uploadAudio,
  uploadSrt,
  updateScene,
  updateSceneStatus,
  buildCapcutProject,
  getVideoGuide,
  updateVideoGuide,
  generateShotlist,
  generateScenePrompt,
  streamGenerateAllPrompts,
  bulkCreateScenes,
} from "@/lib/api";
import type { BatchPromptEvent } from "@/lib/api";
import type { Video, Script, Scene } from "@/lib/api";

type Tab = "brainstorm" | "script" | "narration" | "audio" | "visual_guide" | "edit_guide" | "shotlist" | "assets" | "export";

const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "brainstorm", label: "Lên kịch bản", icon: MessageSquare },
  { id: "script", label: "Kịch bản", icon: FileText },
  { id: "narration", label: "Nội dung", icon: Mic },
  { id: "audio", label: "Âm thanh", icon: Music },
  { id: "visual_guide", label: "Hình ảnh", icon: Palette },
  { id: "edit_guide", label: "Cách edit", icon: Scissors },
  { id: "shotlist", label: "Danh sách cảnh", icon: List },
  { id: "assets", label: "Tài nguyên", icon: Grid3X3 },
  { id: "export", label: "Xuất video", icon: Download },
];

export default function VideoDetailPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const videoId = params.videoId as string;

  const [video, setVideo] = useState<Video | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("brainstorm");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [narration, setNarration] = useState<{ content: string; exists: boolean; updated_at: string | null } | null>(null);
  const [visualGuide, setVisualGuide] = useState<{ content: string; exists: boolean; updated_at: string | null } | null>(null);
  const [editGuide, setEditGuide] = useState<{ content: string; exists: boolean; updated_at: string | null } | null>(null);

  const fetchData = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const videoData = await getVideo(projectId, videoId);
      setVideo(videoData);

      const [scriptData, scenesData] = await Promise.allSettled([
        getScript(projectId, videoId),
        getScenes(projectId, videoId),
      ]);

      if (scriptData.status === "fulfilled" && scriptData.value?.content) setScript(scriptData.value);
      if (scenesData.status === "fulfilled") setScenes(scenesData.value);

      setError(null);
    } catch (err) {
      if (!silent) setError("Không thể tải dữ liệu video.");
      console.error(err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId, videoId]);

  useEffect(() => {
    const guideMap: Record<string, [typeof narration, typeof setNarration, string]> = {
      narration: [narration, setNarration, "narration"],
      visual_guide: [visualGuide, setVisualGuide, "visual_guide"],
      edit_guide: [editGuide, setEditGuide, "edit_guide"],
    };
    const entry = guideMap[activeTab];
    if (entry && entry[0] === null) {
      getVideoGuide(projectId, videoId, entry[2]).then(entry[1]);
    }
  }, [activeTab]);

  const handleApproveScene = async (sceneNumber: number) => {
    try {
      await updateSceneStatus(projectId, videoId, sceneNumber, "approved");
      setScenes((prev) =>
        prev.map((s) =>
          s.scene_number === sceneNumber ? { ...s, status: "approved" } : s
        )
      );
      if (selectedScene?.scene_number === sceneNumber) {
        setSelectedScene((prev) =>
          prev ? { ...prev, status: "approved" } : null
        );
      }
    } catch (err) {
      console.error("Failed to approve scene:", err);
    }
  };

  const handleRedoScene = async (sceneNumber: number) => {
    try {
      await updateSceneStatus(projectId, videoId, sceneNumber, "pending");
      setScenes((prev) =>
        prev.map((s) =>
          s.scene_number === sceneNumber ? { ...s, status: "pending" } : s
        )
      );
      if (selectedScene?.scene_number === sceneNumber) {
        setSelectedScene((prev) =>
          prev ? { ...prev, status: "pending" } : null
        );
      }
    } catch (err) {
      console.error("Failed to redo scene:", err);
    }
  };

  const handleUpdatePrompt = async (sceneNumber: number, prompt: string) => {
    try {
      await updateScene(projectId, videoId, sceneNumber, { veo3_prompt: prompt });
      setScenes((prev) =>
        prev.map((s) =>
          s.scene_number === sceneNumber ? { ...s, veo3_prompt: prompt } : s
        )
      );
      if (selectedScene?.scene_number === sceneNumber) {
        setSelectedScene((prev) => (prev ? { ...prev, veo3_prompt: prompt } : null));
      }
    } catch (err) {
      console.error("Failed to update prompt:", err);
    }
  };

  const handleBuildCapcut = async () => {
    try {
      setExportStatus("building");
      const result = await buildCapcutProject(projectId, videoId);
      setExportStatus(result.status);
    } catch (err) {
      setExportStatus("error");
      console.error("Failed to build CapCut project:", err);
    }
  };

  const allScenesApproved =
    scenes.length > 0 && scenes.every((s) => s.status === "approved");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 indigo-500 animate-spin" />
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="bg-rose-50 rounded-2xl p-6 text-center">
        <p className="text-[13px] text-rose-500 font-medium">{error || "Không tìm thấy video"}</p>
        <Link href={`/projects/${projectId}`} className="mt-3 inline-block text-[12px] text-rose-400 hover:text-rose-600 underline">Quay lại dự án</Link>
      </div>
    );
  }

  return (
    <div>
      {/* Back Link */}
      <Link
        href={`/projects/${projectId}`}
        className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-indigo-500 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Quay lại dự án
      </Link>

      {/* Video Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-800">{video.title}</h1>
          {video.created_at && (
            <p className="text-[12px] text-gray-400 mt-1">
              Ngày tạo {new Date(video.created_at).toLocaleDateString()}
            </p>
          )}
        </div>
        <StatusBadge status={video.status} />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-100 mb-6">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-[13px] font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? "border-indigo-500 text-indigo-600"
                    : "border-transparent text-gray-400 hover:text-gray-600"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {/* Brainstorm Tab */}
        {activeTab === "brainstorm" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[17px] font-bold text-gray-800">Lên kịch bản</h2>
              {script?.content && (
                <button
                  onClick={() => setActiveTab("script")}
                  className="flex items-center gap-1.5 text-sm text-emerald-600 hover:text-emerald-700 transition-colors font-medium"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Đã có kịch bản — xem
                </button>
              )}
            </div>
            <ChatPanel
              projectId={projectId}
              videoId={videoId}
              onFinalized={() => fetchData(true)}
            />
          </div>
        )}

        {/* Script Tab — kịch bản đầy đủ */}
        {activeTab === "script" && (
          <ScriptTab script={script} />
        )}

        {/* Narration Tab — nội dung voice */}
        {activeTab === "narration" && (
          <div>
            <h2 className="text-[17px] font-bold text-gray-800 mb-1">Nội dung voice</h2>
            <p className="text-[12px] text-gray-400 mb-4">Text sạch để ghi âm — không có ghi chú sản xuất, nguồn sử liệu.</p>
            {narration === null ? (
              <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-indigo-500 animate-spin" /></div>
            ) : (
              <GuideEditor
                content={narration.content}
                exists={narration.exists}
                updatedAt={narration.updated_at}
                onSave={async (c) => { await updateVideoGuide(projectId, videoId, "narration", c); const g = await getVideoGuide(projectId, videoId, "narration"); setNarration(g); }}
                placeholder="Nội dung voice — chỉ phần lời đọc, không ghi chú..."
                emptyMessage="Chưa có nội dung voice. Vào tab Lên kịch bản, chat với Claude rồi bấm Chốt."
              />
            )}
          </div>
        )}

        {/* Audio Tab */}
        {activeTab === "audio" && (
          <AudioSrtTab projectId={projectId} videoId={videoId} video={video} onUploadDone={() => fetchData(true)} />
        )}

        {/* Visual Guide Tab */}
        {activeTab === "visual_guide" && (
          <div>
            <h2 className="text-[17px] font-bold text-gray-800 mb-4">Quy định hình ảnh</h2>
            <TemplatePicker
              projectId={projectId}
              videoId={videoId}
              targetGuide="video_visual_guide"
              onApplied={async () => { const g = await getVideoGuide(projectId, videoId, "visual_guide"); setVisualGuide(g); }}
            />
            {visualGuide === null ? (
              <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-indigo-500 animate-spin" /></div>
            ) : (
              <GuideEditor
                content={visualGuide.content}
                exists={visualGuide.exists}
                updatedAt={visualGuide.updated_at}
                onSave={async (c) => { await updateVideoGuide(projectId, videoId, "visual_guide", c); const g = await getVideoGuide(projectId, videoId, "visual_guide"); setVisualGuide(g); }}
                placeholder="Nhập quy định hình ảnh cho video..."
                emptyMessage="Chưa có quy định hình ảnh. Chọn từ kho tài nguyên ở trên hoặc tạo mới."
              />
            )}
          </div>
        )}

        {/* Edit Guide Tab */}
        {activeTab === "edit_guide" && (
          <div>
            <h2 className="text-[17px] font-bold text-gray-800 mb-4">Hướng dẫn edit</h2>
            <TemplatePicker
              projectId={projectId}
              videoId={videoId}
              targetGuide="video_edit_guide"
              onApplied={async () => { const g = await getVideoGuide(projectId, videoId, "edit_guide"); setEditGuide(g); }}
            />
            {editGuide === null ? (
              <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-indigo-500 animate-spin" /></div>
            ) : (
              <GuideEditor
                content={editGuide.content}
                exists={editGuide.exists}
                updatedAt={editGuide.updated_at}
                onSave={async (c) => { await updateVideoGuide(projectId, videoId, "edit_guide", c); const g = await getVideoGuide(projectId, videoId, "edit_guide"); setEditGuide(g); }}
                placeholder="Nhập hướng dẫn edit video..."
                emptyMessage="Chưa có hướng dẫn edit. Chọn từ kho tài nguyên ở trên hoặc tạo mới."
              />
            )}
          </div>
        )}

        {/* Shot List Tab */}
        {activeTab === "shotlist" && (
          <>
          <FlowLoginBanner />
          <ShotlistTab
            scenes={scenes}
            projectId={projectId}
            videoId={videoId}
            onApprove={handleApproveScene}
            onRedo={handleRedoScene}
            onClickScene={setSelectedScene}
            onScenesUpdated={fetchData}
          />
          </>
        )}

        {/* Assets Tab */}
        {activeTab === "assets" && (
          <div>
            <FlowLoginBanner />
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[17px] font-bold text-gray-800">
                Tài nguyên đã tạo ({scenes.length} cảnh)
              </h2>
              {scenes.length > 0 && (
                <div className="flex items-center gap-2">
                  {scenes.filter(s => s.veo3_prompt && !s.asset_path).length > 0 && (
                    <button className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold rounded-xl bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 transition-colors shadow-sm">
                      <Grid3X3 className="w-4 h-4" />
                      Tạo ảnh/video còn thiếu ({scenes.filter(s => s.veo3_prompt && !s.asset_path).length})
                    </button>
                  )}
                  {scenes.filter(s => s.veo3_prompt).length > 0 && (
                    <button className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold rounded-xl bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50 transition-colors shadow-sm">
                      <Grid3X3 className="w-4 h-4" />
                      Tạo lại tất cả
                    </button>
                  )}
                </div>
              )}
            </div>
            {scenes.length === 0 ? (
              <div className="bg-white rounded-2xl p-8 text-center">
                <div className="w-14 h-14 bg-violet-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
                  <Grid3X3 className="w-7 h-7 text-violet-500" />
                </div>
                <p className="text-[13px] text-gray-400">Chưa có tài nguyên. Tạo danh sách cảnh trước.</p>
              </div>
            ) : (
              <SceneTimeline
                scenes={scenes}
                projectId={projectId}
                videoId={videoId}
                onApprove={handleApproveScene}
                onRedo={handleRedoScene}
                onClickScene={setSelectedScene}
              />
            )}
          </div>
        )}

        {/* Export Tab */}
        {activeTab === "export" && (
          <div className="max-w-2xl">
            <h2 className="text-[17px] font-bold text-gray-800 mb-4">
              Xuất video
            </h2>

            <div className="bg-white border border-gray-100 rounded-2xl p-6 mb-6 shadow-sm">
              <h3 className="text-sm font-medium text-gray-700 mb-4">
                Tổng kết xuất video
              </h3>
              {scenes.length === 0 ? (
                <p className="text-sm text-gray-400">Chưa có cảnh nào.</p>
              ) : (
                <div className="space-y-2">
                  {scenes.map((scene) => (
                    <div
                      key={scene.scene_number}
                      className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                    >
                      <span className="text-sm text-gray-600">
                        Cảnh {scene.scene_number}
                      </span>
                      <div className="flex items-center gap-2">
                        {scene.status === "approved" ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-amber-500" />
                        )}
                        <StatusBadge status={scene.status} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={handleBuildCapcut}
              disabled={!allScenesApproved || exportStatus === "building"}
              className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-indigo-500 text-white font-semibold rounded-2xl hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-200"
            >
              {exportStatus === "building" ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Đang tạo project CapCut...
                </>
              ) : (
                <>
                  <Package className="w-5 h-5" />
                  Tạo project CapCut
                </>
              )}
            </button>

            {!allScenesApproved && scenes.length > 0 && (
              <p className="text-xs text-amber-600 mt-3 text-center">
                Tất cả cảnh phải được duyệt trước khi xuất video.
              </p>
            )}

            {exportStatus === "error" && (
              <p className="text-xs text-rose-600 mt-3 text-center">
                Xuất video thất bại. Vui lòng thử lại.
              </p>
            )}

            {exportStatus && exportStatus !== "building" && exportStatus !== "error" && (
              <p className="text-xs text-emerald-600 mt-3 text-center">
                Xuất video thành công.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Scene Detail Modal */}
      {selectedScene && (
        <SceneDetailModal
          scene={selectedScene}
          onClose={() => setSelectedScene(null)}
          onApprove={handleApproveScene}
          onRedo={handleRedoScene}
          onUpdatePrompt={handleUpdatePrompt}
        />
      )}
    </div>
  );
}

// ---- Sub-components ----

function ScriptTab({ script }: { script: Script | null }) {
  if (!script) {
    return (
      <div className="bg-white rounded-2xl p-8 text-center">
        <div className="w-14 h-14 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <FileText className="w-7 h-7 text-indigo-500" />
        </div>
        <p className="text-gray-500">
          Chưa có kịch bản. Vào tab &quot;Lên kịch bản&quot; để chat với Claude rồi bấm &quot;Chốt&quot;.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-[17px] font-bold text-gray-800">Kịch bản</h2>
          <StatusBadge status={script.status} />
        </div>
        <p className="text-[12px] text-gray-400">Bối cảnh, nguồn sử liệu, bố cục, ghi chú sản xuất</p>
      </div>

      <div className="bg-white rounded-2xl p-6">
        <div className="prose prose-sm max-w-none">
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
            {script.content}
          </pre>
        </div>
      </div>

      {script.updated_at && (
        <p className="text-xs text-gray-400 mt-3">
          Cập nhật lần cuối: {new Date(script.updated_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}

function AudioSrtTab({ projectId, videoId, video, onUploadDone }: { projectId: string; videoId: string; video: Video; onUploadDone: () => void }) {
  const [srtUploading, setSrtUploading] = useState(false);
  const [srtFileName, setSrtFileName] = useState<string | null>(null);
  const [srtDragging, setSrtDragging] = useState(false);
  const [audioFileName, setAudioFileName] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [srtError, setSrtError] = useState<string | null>(null);
  const [srtSuccess, setSrtSuccess] = useState(false);
  const [audioSuccess, setAudioSuccess] = useState(false);
  const srtInputRef = useRef<HTMLInputElement>(null);

  const hasSrt = !!video.srt_path || !!srtFileName;
  const hasAudio = !!video.audio_path || !!audioFileName;

  const handleAudioUpload = async (file: File) => {
    setAudioError(null);
    setAudioSuccess(false);
    try {
      await uploadAudio(projectId, videoId, file);
      setAudioFileName(file.name);
      setAudioSuccess(true);
      setTimeout(() => setAudioSuccess(false), 3000);
      onUploadDone();
    } catch {
      setAudioError("Upload âm thanh thất bại. Thử lại.");
    }
  };

  const handleSrtUpload = async (file: File) => {
    setSrtUploading(true);
    setSrtError(null);
    setSrtSuccess(false);
    try {
      await uploadSrt(projectId, videoId, file);
      setSrtFileName(file.name);
      setSrtSuccess(true);
      setTimeout(() => setSrtSuccess(false), 3000);
      onUploadDone();
    } catch {
      setSrtError("Upload SRT thất bại. Thử lại.");
    } finally {
      setSrtUploading(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      {/* Audio */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-[17px] font-bold text-gray-800">Âm thanh thuyết minh</h2>
          {(hasAudio || audioSuccess) && (
            <span className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-lg ${audioSuccess ? "text-emerald-700 bg-emerald-100" : "text-emerald-600 bg-emerald-50"}`}>
              <CheckCircle2 className="w-3 h-3" /> {audioSuccess ? `${audioFileName} — upload thành công!` : audioFileName || "Đã có file"}
            </span>
          )}
        </div>
        <AudioUpload onUpload={handleAudioUpload} />
        {audioError && <p className="text-[12px] text-rose-500 mt-2">{audioError}</p>}
      </div>

      {/* SRT */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-[17px] font-bold text-gray-800">File phụ đề (SRT)</h2>
          {(hasSrt || srtSuccess) && !srtUploading && (
            <span className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-lg ${srtSuccess ? "text-emerald-700 bg-emerald-100" : "text-emerald-600 bg-emerald-50"}`}>
              <CheckCircle2 className="w-3 h-3" /> {srtSuccess ? `${srtFileName} — upload thành công!` : srtFileName || "Đã có file"}
            </span>
          )}
        </div>
        <input
          ref={srtInputRef}
          type="file"
          accept=".srt"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleSrtUpload(f); e.target.value = ""; }}
          className="hidden"
        />
        <div
          onDragOver={(e) => { e.preventDefault(); setSrtDragging(true); }}
          onDragLeave={() => setSrtDragging(false)}
          onDrop={(e) => { e.preventDefault(); setSrtDragging(false); const f = e.dataTransfer.files[0]; if (f) handleSrtUpload(f); }}
          onClick={() => srtInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
            srtDragging ? "border-indigo-400 bg-indigo-50" : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
          }`}
        >
          {srtUploading ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-[13px] text-gray-500">Đang tải lên...</p>
            </div>
          ) : hasSrt ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-emerald-500" />
              </div>
              <p className="text-[13px] font-medium text-emerald-600">{srtFileName || "subtitles.srt"}</p>
              <p className="text-[12px] text-indigo-500 font-medium">Bấm hoặc kéo thả để thay file khác</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-sky-50 flex items-center justify-center">
                <FileText className="w-6 h-6 text-sky-500" />
              </div>
              <div>
                <p className="text-[13px] font-medium text-gray-600">Kéo thả hoặc bấm để chọn file SRT</p>
                <p className="text-[11px] text-gray-400 mt-1">File .srt — dùng để chia cảnh tự động</p>
              </div>
            </div>
          )}
        </div>
        {srtError && <p className="text-[12px] text-rose-500 mt-2">{srtError}</p>}
      </div>
    </div>
  );
}

function ShotlistTab({
  scenes,
  projectId,
  videoId,
  onApprove,
  onRedo,
  onClickScene,
  onScenesUpdated,
}: {
  scenes: Scene[];
  projectId: string;
  videoId: string;
  onApprove: (n: number) => void;
  onRedo: (n: number) => void;
  onClickScene: (scene: Scene) => void;
  onScenesUpdated: () => void;
}) {
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [promptingScenes, setPromptingScenes] = useState<Set<number>>(new Set());
  const [promptingAll, setPromptingAll] = useState(false);
  const [batchStatus, setBatchStatus] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<string | null>(null);
  const [batchErrors, setBatchErrors] = useState<string[]>([]);

  const handleGenerate = async () => {
    if (scenes.length > 0 && !confirm("Sẽ tạo lại danh sách cảnh từ SRT (xóa danh sách cũ). Tiếp tục?")) return;
    setGenerating(true);
    setGenError(null);
    try {
      const result = await generateShotlist(projectId, videoId);
      if (result.status === "ok" && result.scenes) {
        await bulkCreateScenes(projectId, videoId, result.scenes);
        onScenesUpdated();
      } else {
        setGenError(result.message || "Không tạo được danh sách cảnh");
      }
    } catch {
      setGenError("Lỗi kết nối Chat Bridge. Đảm bảo Chat Bridge đang chạy.");
    } finally {
      setGenerating(false);
    }
  };

  // Tạo prompt cho 1 scene (nút trên card)
  const handleGeneratePrompt = async (sceneNumber: number) => {
    setPromptingScenes((prev) => new Set(prev).add(sceneNumber));
    try {
      const result = await generateScenePrompt(projectId, videoId, sceneNumber);
      if (result.status === "ok" && result.veo3_prompt) {
        await updateScene(projectId, videoId, sceneNumber, {
          veo3_prompt: result.veo3_prompt,
          visual_type: (result.visual_type as "image" | "video") || "image",
          mood: result.mood || "",
        });
        onScenesUpdated();
      } else {
        setGenError(`Cảnh ${sceneNumber}: ${result.message || "Không tạo được prompt"}`);
      }
    } catch {
      setGenError(`Cảnh ${sceneNumber}: Lỗi kết nối Chat Bridge.`);
    } finally {
      setPromptingScenes((prev) => { const n = new Set(prev); n.delete(sceneNumber); return n; });
    }
  };

  // Đầu não + 10 workers song song (SSE stream)
  const handleGenerateAllPrompts = async (mode: 'all' | 'missing' = 'missing') => {
    setPromptingAll(true);
    setGenError(null);
    setBatchStatus(null);
    setBatchProgress(null);
    setBatchErrors([]);
    if (mode === 'all') {
      setPromptingScenes(new Set(scenes.map((s) => s.scene_number)));
    } else {
      setPromptingScenes(new Set(scenes.filter((s) => !s.veo3_prompt).map((s) => s.scene_number)));
    }

    await streamGenerateAllPrompts(projectId, videoId, async (event: BatchPromptEvent) => {
      if (event.type === "status") {
        setBatchStatus(event.message || null);
      } else if (event.type === "plan_done") {
        setBatchStatus("Kế hoạch xong — đang tạo prompt song song...");
      } else if (event.type === "scene_done") {
        setBatchProgress(event.progress || null);
        const sn = event.scene_number!;
        // Xóa scene khỏi danh sách đang xử lý
        setPromptingScenes((prev) => { const n = new Set(prev); n.delete(sn); return n; });

        if (event.status === "ok" && event.veo3_prompt) {
          // Cập nhật DB ngay
          try {
            await updateScene(projectId, videoId, sn, {
              veo3_prompt: event.veo3_prompt,
              visual_type: (event.visual_type as "image" | "video") || "image",
              mood: event.mood || "",
            });
          } catch { /* silent — scene vẫn ở DB */ }
          // Refresh data để UI cập nhật
          onScenesUpdated();
        } else {
          setBatchErrors((prev) => [...prev, `Cảnh ${sn}: ${event.message || "Lỗi"}`]);
        }
      } else if (event.type === "all_done") {
        setBatchStatus(null);
        setBatchProgress(null);
        onScenesUpdated();
      } else if (event.type === "error") {
        setGenError(event.message || "Lỗi không xác định");
      }
    }, mode);

    setPromptingAll(false);
    setPromptingScenes(new Set());
  };

  const scenesWithPrompt = scenes.filter((s) => s.veo3_prompt).length;
  const scenesMissingPrompt = scenes.length - scenesWithPrompt;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[17px] font-bold text-gray-800">
          Danh sách cảnh {scenes.length > 0 && `(${scenes.length} cảnh)`}
        </h2>
        <div className="flex items-center gap-2">
          {scenes.length > 0 && scenesMissingPrompt > 0 && (
            <button
              onClick={() => handleGenerateAllPrompts('missing')}
              disabled={promptingAll || promptingScenes.size > 0}
              className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold rounded-xl bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {promptingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Palette className="w-4 h-4" />}
              {promptingAll
                ? `Đang tạo prompt... ${batchProgress || ""}`
                : `Tạo prompt còn thiếu (${scenesMissingPrompt})`}
            </button>
          )}
          {scenes.length > 0 && scenesWithPrompt > 0 && (
            <button
              onClick={() => handleGenerateAllPrompts('all')}
              disabled={promptingAll || promptingScenes.size > 0}
              className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold rounded-xl bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {promptingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Palette className="w-4 h-4" />}
              Tạo lại tất cả prompt
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold rounded-xl bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 transition-colors shadow-sm"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <List className="w-4 h-4" />}
            {generating ? "Đang chia cảnh..." : "Tạo từ SRT"}
          </button>
        </div>
      </div>

      {/* Batch status bar */}
      {batchStatus && (
        <div className="flex items-center gap-2 px-4 py-3 text-[12px] text-indigo-700 bg-indigo-50 rounded-xl mb-4">
          <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
          <span>{batchStatus}</span>
          {batchProgress && <span className="ml-auto font-bold">{batchProgress}</span>}
        </div>
      )}

      {genError && (
        <div className="flex items-center gap-2 px-4 py-3 text-[12px] text-rose-600 bg-rose-50 rounded-xl mb-4">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /> {genError}
        </div>
      )}

      {batchErrors.length > 0 && (
        <div className="px-4 py-3 text-[12px] text-amber-700 bg-amber-50 rounded-xl mb-4 space-y-1">
          {batchErrors.map((e, i) => (
            <div key={i} className="flex items-center gap-2">
              <AlertCircle className="w-3 h-3 flex-shrink-0" /> {e}
            </div>
          ))}
        </div>
      )}

      {scenes.length === 0 ? (
        <div className="bg-white rounded-2xl p-8 text-center">
          <div className="w-14 h-14 bg-sky-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
            <List className="w-7 h-7 text-sky-500" />
          </div>
          <p className="text-[13px] text-gray-400 mb-1">Chưa có danh sách cảnh.</p>
          <p className="text-[12px] text-gray-400">Upload file SRT ở tab Âm thanh, rồi bấm &quot;Tạo từ SRT&quot; để chia cảnh.</p>
        </div>
      ) : (
        <SceneTimeline
          scenes={scenes}
          projectId={projectId}
          videoId={videoId}
          onApprove={onApprove}
          onRedo={onRedo}
          onClickScene={onClickScene}
          onGeneratePrompt={handleGeneratePrompt}
          promptingScenes={promptingScenes}
        />
      )}
    </div>
  );
}
