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
  Trash2,
  Smartphone,
  Users,
  Sparkles,
  Edit3,
  Image,
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
  streamGenerateSceneAssets,
  generateSceneAsset,
  cancelGeneration,
  bulkCreateScenes,
  clearAllPrompts,
  clearAllAssets,
  deleteAllScenes,
  deleteSrt,
  getShortGuide,
  updateShortGuide,
  uploadShortAudio,
  uploadShortSrt,
  getShortSrt,
  deleteShortSrt,
  getShortAudioStatus,
  getShortScenes,
  generateShortShotlist,
  bulkCreateShortScenes,
  deleteAllShortScenes,
  streamGenerateAllShortPrompts,
  streamGenerateShortAssets,
  getCharacters,
  createCharacter,
  deleteCharacter,
  extractCharacters,
  generateCharacterImage,
  generateAllCharacterImages,
  clearCharacterImages,
  clearSceneCharacters,
  getGenerationErrors,
  clearGenerationErrors,
} from "@/lib/api";
import type { BatchPromptEvent, SceneAssetEvent, GenerationError } from "@/lib/api";
import type { Video, Script, Scene, Character, SceneBulkItem } from "@/lib/api";
import Markdown from "react-markdown";

type Tab = "brainstorm" | "script" | "narration" | "audio" | "visual_guide" | "edit_guide" | "shotlist" | "characters"
  | "short_brainstorm" | "short_script" | "short_audio" | "short_shotlist";

const tabs: { id: Tab; label: string; icon: React.ElementType; group?: string }[] = [
  { id: "brainstorm", label: "Lên kịch bản", icon: MessageSquare },
  { id: "script", label: "Kịch bản", icon: FileText },
  { id: "narration", label: "Nội dung", icon: Mic },
  { id: "audio", label: "Âm thanh", icon: Music },
  { id: "visual_guide", label: "Hình ảnh", icon: Palette },
  { id: "edit_guide", label: "Cách edit", icon: Scissors },
  { id: "shotlist", label: "Cảnh & Tài nguyên", icon: List },
  { id: "characters", label: "Nhân vật", icon: Users },
  // Short tabs
  { id: "short_brainstorm", label: "Short: Ý tưởng", icon: Smartphone, group: "short" },
  { id: "short_script", label: "Short: Kịch bản", icon: Smartphone, group: "short" },
  { id: "short_audio", label: "Short: Âm thanh", icon: Smartphone, group: "short" },
  { id: "short_shotlist", label: "Short: Cảnh", icon: Smartphone, group: "short" },
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
  // Short state
  const [shortScript, setShortScript] = useState<{ content: string; exists: boolean; updated_at: string | null } | null>(null);
  const [shortNarration, setShortNarration] = useState<{ content: string; exists: boolean; updated_at: string | null } | null>(null);
  // Characters state
  const [characters, setCharacters] = useState<Character[]>([]);
  const [charactersLoading, setCharactersLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [generatingImages, setGeneratingImages] = useState<Set<string>>(new Set());
  const [generatingAll, setGeneratingAll] = useState(false);
  const [flowLoggedIn, setFlowLoggedIn] = useState(false);

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
    // Lazy-load short guides
    if (activeTab === "short_script") {
      if (shortScript === null) getShortGuide(projectId, videoId, "script").then(setShortScript);
      if (shortNarration === null) getShortGuide(projectId, videoId, "narration").then(setShortNarration);
    }
    // Lazy-load characters
    if (activeTab === "characters" && characters.length === 0 && !charactersLoading) {
      fetchCharacters();
    }
  }, [activeTab]);

  const fetchCharacters = async () => {
    setCharactersLoading(true);
    try { const chars = await getCharacters(projectId, videoId); setCharacters(chars); } catch {} finally { setCharactersLoading(false); }
  };

  const handleDeleteCharacter = async (characterId: string) => {
    if (!confirm("Xóa nhân vật này?")) return;
    try { await deleteCharacter(projectId, videoId, characterId); setCharacters((prev) => prev.filter((c) => c.id !== characterId)); } catch {}
  };

  const handleExtractCharacters = async () => {
    setExtracting(true);
    setExtractError(null);
    try {
      const result = await extractCharacters(projectId, videoId);
      if (result.status === "ok" && result.characters) {
        for (const charData of result.characters) {
          await createCharacter(projectId, videoId, { ...charData, project_id: projectId, video_id: videoId, visual_prompt_base: charData.visual_prompt_base || "" });
        }
        await fetchCharacters();
      } else {
        setExtractError(result.message || "Không trích xuất được nhân vật.");
      }
    } catch (e: unknown) {
      setExtractError(e instanceof Error ? e.message : "Lỗi trích xuất nhân vật.");
    } finally { setExtracting(false); }
  };

  const handleGenerateImage = async (characterId: string) => {
    if (!flowLoggedIn) { alert("Vui lòng đăng nhập Google Flow trước."); return; }
    setGeneratingImages((prev) => new Set(prev).add(characterId));
    try {
      await generateCharacterImage(projectId, videoId, characterId);
      await fetchCharacters();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("FLOW_NOT_LOGGED_IN") || msg.includes("401")) {
        setFlowLoggedIn(false);
      } else {
        alert(msg || "Lỗi tạo ảnh nhân vật.");
      }
    } finally {
      setGeneratingImages((prev) => { const next = new Set(prev); next.delete(characterId); return next; });
    }
  };

  const handleGenerateAllImages = async () => {
    if (!flowLoggedIn) { alert("Vui lòng đăng nhập Google Flow trước."); return; }
    setGeneratingAll(true);
    try {
      await generateAllCharacterImages(projectId, videoId);
      await fetchCharacters();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("FLOW_NOT_LOGGED_IN") || msg.includes("401")) {
        setFlowLoggedIn(false);
      } else {
        alert(msg || "Lỗi tạo ảnh nhân vật.");
      }
    } finally { setGeneratingAll(false); }
  };

  const handleClearCharacterImages = async () => {
    if (!confirm("Xóa tất cả ảnh nhân vật đã tạo?")) return;
    try {
      await clearCharacterImages(projectId, videoId);
      await fetchCharacters();
    } catch {
      alert("Lỗi xóa ảnh nhân vật.");
    }
  };

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

  const handleApproveAll = async () => {
    const pending = scenes.filter((s) => s.status !== "approved");
    if (pending.length === 0) return;
    try {
      await Promise.all(pending.map((s) => updateSceneStatus(projectId, videoId, s.scene_number, "approved")));
      setScenes((prev) => prev.map((s) => ({ ...s, status: "approved" })));
    } catch (err) {
      console.error("Failed to approve all:", err);
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
      const result = await buildCapcutProject(projectId, videoId) as { status: string; message?: string };
      if (result.status === "not_implemented") {
        setExportStatus("not_implemented:" + (result.message || ""));
      } else {
        setExportStatus(result.status);
      }
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
          <div className="flex items-center gap-3 mt-1">
            {video.created_at && (
              <p className="text-[12px] text-gray-400">
                Ngày tạo {new Date(video.created_at).toLocaleDateString()}
              </p>
            )}
            <div className="flex items-center gap-2">
              <span className="text-[12px] text-gray-400 whitespace-nowrap">Flow Project ID</span>
              <input
                id="flow-project-id-input"
                className="text-[12px] text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-2 py-1 w-80 focus:outline-none focus:border-indigo-300"
                placeholder="VD: a86abc69-5508-4d56-931e-e587312105f2"
                defaultValue={video.flow_project_id || ""}
              />
              <button
                className="text-[11px] px-3 py-1 rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 transition-colors font-semibold"
                onClick={async () => {
                  const input = document.getElementById("flow-project-id-input") as HTMLInputElement;
                  const val = input?.value.trim() || "";
                  try {
                    const { updateVideo } = await import("@/lib/api");
                    await updateVideo(projectId, videoId, { flow_project_id: val });
                    setVideo((prev) => prev ? { ...prev, flow_project_id: val } : prev);
                    input.style.borderColor = "#10b981";
                    setTimeout(() => { input.style.borderColor = ""; }, 1500);
                  } catch {
                    input.style.borderColor = "#ef4444";
                    setTimeout(() => { input.style.borderColor = ""; }, 1500);
                  }
                }}
              >Lưu</button>
            </div>
          </div>
        </div>
        <StatusBadge status={video.status} />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-100 mb-6 overflow-x-auto">
        <div className="flex gap-1 min-w-max">
          {tabs.map((tab, i) => {
            const Icon = tab.icon;
            const isFirstShort = tab.group === "short" && (i === 0 || tabs[i - 1].group !== "short");
            return (
              <span key={tab.id} className="flex items-center">
                {isFirstShort && (
                  <span className="mx-2 text-gray-600 text-xs select-none">|</span>
                )}
                <button
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-[13px] font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? tab.group === "short" ? "border-purple-500 text-purple-500" : "border-indigo-500 text-indigo-600"
                      : "border-transparent text-gray-400 hover:text-gray-600"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              </span>
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

        {/* Cảnh & Tài nguyên Tab */}
        {activeTab === "shotlist" && (
          <>
          <FlowLoginBanner />
          <ShotlistTab
            scenes={scenes}
            setScenes={setScenes}
            projectId={projectId}
            videoId={videoId}
            onApprove={handleApproveScene}
            onRedo={handleRedoScene}
            onApproveAll={handleApproveAll}
            allScenesApproved={allScenesApproved}
            onClickScene={setSelectedScene}
            onScenesUpdated={fetchData}
            onBuildCapcut={handleBuildCapcut}
            exportStatus={exportStatus}
          />
          </>
        )}

        {/* Short: Lên ý tưởng — Chat brainstorm (context = video gốc) */}
        {activeTab === "short_brainstorm" && (
          <ChatPanel
            projectId={projectId}
            videoId={videoId}
            chatType="short"
          />
        )}

        {/* Short: Kịch bản + Nội dung voice */}
        {activeTab === "short_script" && (
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">Kịch bản Short</h3>
              <GuideEditor
                content={shortScript?.content || ""}
                exists={shortScript?.exists || false}
                updatedAt={shortScript?.updated_at || null}
                onSave={async (content) => {
                  await updateShortGuide(projectId, videoId, "script", content);
                  const updated = await getShortGuide(projectId, videoId, "script");
                  setShortScript(updated);
                }}
              />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">Nội dung voice Short</h3>
              <GuideEditor
                content={shortNarration?.content || ""}
                exists={shortNarration?.exists || false}
                updatedAt={shortNarration?.updated_at || null}
                onSave={async (content) => {
                  await updateShortGuide(projectId, videoId, "narration", content);
                  const updated = await getShortGuide(projectId, videoId, "narration");
                  setShortNarration(updated);
                }}
              />
            </div>
          </div>
        )}

        {/* Short: Âm thanh — Upload audio + SRT */}
        {activeTab === "short_audio" && (
          <ShortAudioTab projectId={projectId} videoId={videoId} />
        )}

        {/* Short: Cảnh & Tài nguyên */}
        {activeTab === "short_shotlist" && (
          <ShortShotlistTab projectId={projectId} videoId={videoId} onClickScene={setSelectedScene} />
        )}

        {/* Nhân vật Tab */}
        {activeTab === "characters" && (
          charactersLoading ? (
            <div className="flex items-center justify-center py-20"><Loader2 className="w-7 h-7 text-indigo-500 animate-spin" /></div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-[17px] font-bold text-gray-800">Nhân vật ({characters.length})</h2>
              </div>

              <FlowLoginBanner onStatusChange={setFlowLoggedIn} />

              {/* Extract from script */}
              <div className="bg-white rounded-2xl p-4 mb-6 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleExtractCharacters}
                  disabled={extracting}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-500 text-white text-[13px] font-semibold rounded-xl hover:bg-indigo-600 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {extracting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  Trích xuất từ kịch bản
                </button>
                {characters.length > 0 && (
                  <>
                    <button
                      onClick={handleClearCharacterImages}
                      disabled={generatingAll}
                      className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 text-[13px] font-semibold rounded-xl hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ml-auto"
                    >
                      <Trash2 className="w-4 h-4" />
                      Xóa ảnh nhân vật
                    </button>
                    <button
                      onClick={handleGenerateAllImages}
                      disabled={generatingAll}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white text-[13px] font-semibold rounded-xl hover:bg-purple-600 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {generatingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Image className="w-4 h-4" />}
                      {generatingAll ? "Đang tạo ảnh..." : "Tạo ảnh tất cả"}
                    </button>
                  </>
                )}
                {extractError && <p className="text-[12px] text-rose-500 w-full">{extractError}</p>}
              </div>

              {characters.length === 0 ? (
                <div className="bg-white rounded-2xl p-12 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center mx-auto mb-4"><Users className="w-7 h-7 text-indigo-500" /></div>
                  <h3 className="text-[15px] font-semibold text-gray-700 mb-1">Chưa có nhân vật nào</h3>
                  <p className="text-[13px] text-gray-400">Trích xuất nhân vật từ kịch bản video hoặc tạo thủ công</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {characters.map((char) => (
                    <div key={char.id} className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                      {/* Reference image or placeholder */}
                      <div className="h-40 bg-gray-50 flex items-center justify-center">
                        {char.reference_image_path ? (
                          <img src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${char.reference_image_path}`} alt={char.name} className="w-full h-full object-cover" />
                        ) : (
                          <Image className="w-10 h-10 text-gray-300" />
                        )}
                      </div>

                      <div className="p-4">
                        {/* Name */}
                        <h3 className="text-[15px] font-bold text-gray-800">{char.name}</h3>
                        {char.historical_name && <p className="text-[12px] text-gray-400 mt-0.5">{char.historical_name}</p>}

                        {/* Era + Age badges */}
                        {(char.era || char.age_range) && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {char.era && <span className="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-[11px] font-medium rounded-lg">{char.era}</span>}
                            {char.age_range && <span className="px-2 py-0.5 bg-emerald-50 text-emerald-600 text-[11px] font-medium rounded-lg">{char.age_range}</span>}
                          </div>
                        )}

                        {/* Reference description */}
                        {char.reference_description && (
                          <p className="text-[12px] text-gray-500 mt-2 line-clamp-3">{char.reference_description}</p>
                        )}

                        {/* Visual prompt base */}
                        {char.visual_prompt_base && (
                          <p className="text-[11px] text-gray-400 italic mt-2 line-clamp-2">{char.visual_prompt_base}</p>
                        )}

                        {/* Color palette dots */}
                        {char.color_palette && Object.keys(char.color_palette).length > 0 && (
                          <div className="flex items-center gap-1.5 mt-3">
                            {Object.entries(char.color_palette).map(([name, color]) => (
                              <div key={name} title={name} className="w-5 h-5 rounded-full border border-gray-200" style={{ backgroundColor: color }} />
                            ))}
                          </div>
                        )}

                        {/* Consistency anchors */}
                        {char.consistency_anchors && char.consistency_anchors.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {char.consistency_anchors.map((anchor, i) => (
                              <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-500 text-[10px] rounded-md">{anchor}</span>
                            ))}
                          </div>
                        )}

                        {/* Action buttons */}
                        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-gray-100">
                          <button
                            onClick={() => handleGenerateImage(char.id)}
                            disabled={generatingImages.has(char.id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-600 text-[11px] font-medium rounded-lg hover:bg-indigo-100 disabled:opacity-50 transition-colors"
                          >
                            {generatingImages.has(char.id) ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                            {generatingImages.has(char.id) ? "Đang tạo..." : char.reference_image_path ? "Tạo lại ảnh" : "Tạo ảnh"}
                          </button>
                          <button className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 text-gray-500 text-[11px] font-medium rounded-lg hover:bg-gray-100 transition-colors">
                            <Edit3 className="w-3.5 h-3.5" /> Sửa
                          </button>
                          <button
                            onClick={() => handleDeleteCharacter(char.id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-500 text-[11px] font-medium rounded-lg hover:bg-rose-100 transition-colors ml-auto"
                          >
                            <Trash2 className="w-3.5 h-3.5" /> Xóa
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )
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
        <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-headings:font-bold prose-h1:text-lg prose-h2:text-base prose-h3:text-sm prose-p:text-sm prose-li:text-sm prose-strong:text-gray-700">
          <Markdown>{script.content}</Markdown>
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
            <>
              <span className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-lg ${srtSuccess ? "text-emerald-700 bg-emerald-100" : "text-emerald-600 bg-emerald-50"}`}>
                <CheckCircle2 className="w-3 h-3" /> {srtSuccess ? `${srtFileName} — upload thành công!` : srtFileName || "Đã có file"}
              </span>
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  if (!confirm("Xóa file SRT?")) return;
                  try {
                    await deleteSrt(projectId, videoId);
                    setSrtFileName(null);
                    setSrtSuccess(false);
                    onUploadDone();
                  } catch {
                    setSrtError("Lỗi xóa SRT.");
                  }
                }}
                className="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-lg text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
              >
                <Trash2 className="w-3 h-3" /> Xóa
              </button>
            </>
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

function ShortAudioTab({ projectId, videoId }: { projectId: string; videoId: string }) {
  const [audioUploading, setAudioUploading] = useState(false);
  const [srtUploading, setSrtUploading] = useState(false);
  const [audioName, setAudioName] = useState<string | null>(null);
  const [srtName, setSrtName] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const audioRef = useRef<HTMLInputElement>(null);
  const srtRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getShortAudioStatus(projectId, videoId).then(exists => { if (exists) setAudioName("narration.mp3"); });
    getShortSrt(projectId, videoId).then(data => { if (data.exists) setSrtName("subtitles.srt"); }).catch(() => {});
  }, [projectId, videoId]);

  const handleAudio = async (file: File) => {
    setAudioUploading(true); setMsg(null);
    try { await uploadShortAudio(projectId, videoId, file); setAudioName(file.name); setMsg("Audio short uploaded!"); } catch { setMsg("Lỗi upload audio"); }
    finally { setAudioUploading(false); }
  };
  const handleSrt = async (file: File) => {
    setSrtUploading(true); setMsg(null);
    try { await uploadShortSrt(projectId, videoId, file); setSrtName(file.name); setMsg("SRT short uploaded!"); } catch { setMsg("Lỗi upload SRT"); }
    finally { setSrtUploading(false); }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-[17px] font-bold text-gray-800 mb-4">Âm thanh Short (45-50s)</h2>
        <input ref={audioRef} type="file" accept="audio/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleAudio(f); }} />
        <div onClick={() => audioRef.current?.click()} className="border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer border-gray-200 hover:border-purple-300 hover:bg-gray-50 transition-all">
          {audioUploading ? <Loader2 className="w-8 h-8 mx-auto text-purple-500 animate-spin" /> : audioName ? (
            <p className="text-[13px] text-emerald-600 font-medium">{audioName} — Bấm để thay</p>
          ) : (
            <><Music className="w-8 h-8 mx-auto text-purple-300 mb-2" /><p className="text-[13px] text-gray-500">Bấm hoặc kéo thả file audio short</p></>
          )}
        </div>
      </div>
      <div>
        <h2 className="text-[17px] font-bold text-gray-800 mb-4">File SRT Short</h2>
        <input ref={srtRef} type="file" accept=".srt" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleSrt(f); }} />
        <div onClick={() => srtRef.current?.click()} className="border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer border-gray-200 hover:border-purple-300 hover:bg-gray-50 transition-all">
          {srtUploading ? <Loader2 className="w-8 h-8 mx-auto text-purple-500 animate-spin" /> : srtName ? (
            <p className="text-[13px] text-emerald-600 font-medium">{srtName} — Bấm để thay</p>
          ) : (
            <><FileText className="w-8 h-8 mx-auto text-purple-300 mb-2" /><p className="text-[13px] text-gray-500">Bấm hoặc kéo thả file SRT short</p></>
          )}
        </div>
      </div>
      {msg && <p className="text-[12px] text-emerald-600">{msg}</p>}
    </div>
  );
}

function ShortShotlistTab({ projectId, videoId, onClickScene }: { projectId: string; videoId: string; onClickScene: (scene: Scene) => void }) {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasAudio, setHasAudio] = useState(false);
  const [hasSrt, setHasSrt] = useState(false);

  // Prompt generation state
  const [promptingScenes, setPromptingScenes] = useState<Set<number>>(new Set());
  const [promptingAll, setPromptingAll] = useState(false);
  const [batchStatus, setBatchStatus] = useState<string | null>(null);
  const [batchTotal, setBatchTotal] = useState(0);
  const [batchDone, setBatchDone] = useState(0);
  const [batchErrors, setBatchErrors] = useState<string[]>([]);
  const promptAbortRef = useRef<AbortController | null>(null);

  // Asset generation state
  const [generatingAssets, setGeneratingAssets] = useState(false);
  const [assetStatus, setAssetStatus] = useState<string | null>(null);
  const [assetTotal, setAssetTotal] = useState(0);
  const [assetDone, setAssetDone] = useState(0);
  const [assetErrors, setAssetErrors] = useState<string[]>([]);
  const assetAbortRef = useRef<AbortController | null>(null);

  // Persistent generation error log
  const [genErrorLog, setGenErrorLog] = useState<GenerationError[]>([]);
  const [showErrorLog, setShowErrorLog] = useState(false);

  const fetchScenes = async () => {
    try {
      const data = await getShortScenes(projectId, videoId);
      setScenes(data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchScenes();
    getShortAudioStatus(projectId, videoId).then(setHasAudio);
    getShortSrt(projectId, videoId).then(d => setHasSrt(d.exists)).catch(() => {});
    getGenerationErrors(projectId, videoId).then(setGenErrorLog).catch(() => {});
  }, [projectId, videoId]);

  const handleGenerate = async () => {
    if (scenes.length > 0 && !confirm("Sẽ tạo lại danh sách cảnh từ SRT (xóa cũ). Tiếp tục?")) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await generateShortShotlist(projectId, videoId);
      if (result.status === "ok" && result.scenes) {
        await bulkCreateShortScenes(projectId, videoId, result.scenes as SceneBulkItem[]);
        await fetchScenes();
      } else {
        setError("Không tạo được danh sách cảnh");
      }
    } catch {
      setError("Lỗi kết nối Chat Bridge. Đảm bảo Chat Bridge đang chạy.");
    } finally {
      setGenerating(false);
    }
  };

  // Tạo prompt cho 1 scene
  const handleGeneratePrompt = async (sceneNumber: number) => {
    setPromptingScenes(prev => new Set(prev).add(sceneNumber));
    try {
      const result = await generateScenePrompt(projectId, videoId, sceneNumber);
      if (result.status === "ok" && result.veo3_prompt) {
        const updatedFields: Record<string, unknown> = {
          veo3_prompt: result.veo3_prompt,
          visual_type: (result.visual_type as "image" | "video") || "image",
          mood: result.mood || "",
        };
        if ((result as Record<string, unknown>).flow_characters) updatedFields.flow_characters = (result as Record<string, unknown>).flow_characters;
        await updateScene(projectId, videoId, sceneNumber, updatedFields, true);
        setScenes(prev => prev.map(s => s.scene_number === sceneNumber ? { ...s, ...updatedFields } : s));
      } else {
        setError(`Cảnh ${sceneNumber}: ${result.message || "Không tạo được prompt"}`);

      }
    } catch {
      setError(`Cảnh ${sceneNumber}: Lỗi kết nối Chat Bridge.`);
    } finally {
      setPromptingScenes(prev => { const n = new Set(prev); n.delete(sceneNumber); return n; });
    }
  };

  // Tạo prompt hàng loạt (SSE stream)
  const handleGenerateAllPrompts = async (mode: 'all' | 'missing' = 'missing') => {
    const targetScenes = mode === 'all'
      ? scenes.map(s => s.scene_number)
      : scenes.filter(s => !s.veo3_prompt).map(s => s.scene_number);
    const abortController = new AbortController();
    promptAbortRef.current = abortController;
    setPromptingAll(true);
    setError(null);
    setBatchStatus("Đang khởi tạo...");
    setBatchTotal(targetScenes.length);
    setBatchDone(0);
    setBatchErrors([]);
    setPromptingScenes(new Set(targetScenes));

    await streamGenerateAllShortPrompts(projectId, videoId, async (event: BatchPromptEvent) => {
      if (event.type === "status") {
        setBatchStatus(event.message || null);
      } else if (event.type === "plan_done") {
        setBatchStatus("Kế hoạch xong — đang tạo prompt...");
      } else if (event.type === "scene_done") {
        setBatchDone(prev => prev + 1);
        const sn = event.scene_number!;
        setPromptingScenes(prev => { const n = new Set(prev); n.delete(sn); return n; });
        if (event.status === "ok" && event.veo3_prompt) {
          const updatedFields: Record<string, unknown> = {
            veo3_prompt: event.veo3_prompt,
            visual_type: (event.visual_type as "image" | "video") || "image",
            mood: event.mood || "",
          };
          setScenes(prev => prev.map(s => s.scene_number === sn ? { ...s, ...updatedFields } : s));
        } else {
          setBatchErrors(prev => [...prev, `Cảnh ${sn}: ${event.message || "Lỗi"}`]);
        }
      } else if (event.type === "all_done" || event.type === "stopped") {
        setBatchStatus(event.type === "stopped" ? "Đã dừng" : null);
        setBatchTotal(0);
        setBatchDone(0);
        await fetchScenes();
        getGenerationErrors(projectId, videoId).then(setGenErrorLog).catch(() => {});
        if (event.type === "stopped") setTimeout(() => setBatchStatus(null), 3000);
      } else if (event.type === "error") {
        setError(event.message || "Lỗi không xác định");
      }
    }, mode, abortController.signal);

    promptAbortRef.current = null;
    setPromptingAll(false);
    setPromptingScenes(new Set());
  };

  const handleStopPrompts = () => {
    cancelGeneration(projectId, videoId).catch(() => {});
    promptAbortRef.current?.abort();
    setBatchStatus("Đã dừng");
    setTimeout(() => setBatchStatus(null), 3000);
  };

  // Tạo ảnh/video hàng loạt (SSE stream)
  const handleGenerateAllAssets = async (mode: 'all' | 'missing' = 'missing') => {
    const abortController = new AbortController();
    assetAbortRef.current = abortController;
    setGeneratingAssets(true);
    setError(null);
    setAssetStatus("Đang khởi tạo...");
    const targetCount = mode === 'all'
      ? scenes.filter(s => s.veo3_prompt).length
      : scenes.filter(s => s.veo3_prompt && !s.asset_path).length;
    setAssetTotal(targetCount);
    setAssetDone(0);
    setAssetErrors([]);

    await streamGenerateShortAssets(projectId, videoId, async (event: SceneAssetEvent) => {
      if (event.type === "status") {
        setAssetStatus(event.message || null);
      } else if (event.type === "scene_done") {
        setAssetDone(prev => prev + 1);
        const sn = event.scene_number!;
        if (event.status === "ok" && event.asset_path) {
          setScenes(prev => prev.map(s =>
            s.scene_number === sn ? { ...s, asset_path: event.asset_path!, asset_version: event.version, status: "review" } : s
          ));
        } else {
          setAssetErrors(prev => [...prev, `Cảnh ${sn}: ${event.message || "Lỗi"}`]);
        }
      } else if (event.type === "all_done" || event.type === "stopped") {
        setAssetStatus(event.type === "stopped" ? "Đã dừng" : null);
        setAssetTotal(0);
        setAssetDone(0);
        await fetchScenes();
        getGenerationErrors(projectId, videoId).then(setGenErrorLog).catch(() => {});
        if (event.type === "stopped") setTimeout(() => setAssetStatus(null), 3000);
      } else if (event.type === "error") {
        setError(event.message || "Lỗi không xác định");
      }
    }, mode, abortController.signal);

    assetAbortRef.current = null;
    setGeneratingAssets(false);
  };

  const handleStopAssets = () => {
    cancelGeneration(projectId, videoId).catch(() => {});
    assetAbortRef.current?.abort();
    setAssetStatus("Đã dừng");
    setTimeout(() => setAssetStatus(null), 3000);
  };

  // Tạo ảnh/video cho cảnh đã chọn (từ SceneTimeline floating bar)
  const handleGenerateSelectedAssets = async (sceneNumbers: number[], visualTypeFilter?: 'image' | 'video') => {
    const abortController = new AbortController();
    assetAbortRef.current = abortController;
    setGeneratingAssets(true);
    setError(null);
    setAssetStatus("Đang khởi tạo...");
    setAssetTotal(sceneNumbers.length);
    setAssetDone(0);
    setAssetErrors([]);

    await streamGenerateShortAssets(projectId, videoId, async (event: SceneAssetEvent) => {
      if (event.type === "status") {
        setAssetStatus(event.message || null);
      } else if (event.type === "scene_done") {
        setAssetDone(prev => prev + 1);
        const sn = event.scene_number!;
        if (event.status === "ok" && event.asset_path) {
          setScenes(prev => prev.map(s =>
            s.scene_number === sn ? { ...s, asset_path: event.asset_path!, asset_version: event.version, status: "review" } : s
          ));
        } else {
          setAssetErrors(prev => [...prev, `Cảnh ${sn}: ${event.message || "Lỗi"}`]);
        }
      } else if (event.type === "all_done" || event.type === "stopped") {
        setAssetStatus(event.type === "stopped" ? "Đã dừng" : null);
        setAssetTotal(0);
        setAssetDone(0);
        await fetchScenes();
        getGenerationErrors(projectId, videoId).then(setGenErrorLog).catch(() => {});
        if (event.type === "stopped") setTimeout(() => setAssetStatus(null), 3000);
      } else if (event.type === "error") {
        setError(event.message || "Lỗi không xác định");
      }
    }, 'all', abortController.signal, sceneNumbers, visualTypeFilter);

    assetAbortRef.current = null;
    setGeneratingAssets(false);
  };

  const handleApprove = async (n: number) => {
    try {
      await updateSceneStatus(projectId, videoId, n, "approved", true);
      setScenes(prev => prev.map(s => s.scene_number === n ? { ...s, status: "approved" } : s));
    } catch { /* ignore */ }
  };

  const handleRedo = async (n: number) => {
    try {
      await updateSceneStatus(projectId, videoId, n, "redo", true);
      setScenes(prev => prev.map(s => s.scene_number === n ? { ...s, status: "redo" } : s));
    } catch { /* ignore */ }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-purple-400" /></div>;

  if (!hasAudio || !hasSrt) {
    return (
      <div className="text-center py-12 text-gray-400">
        <Smartphone className="w-12 h-12 mx-auto mb-3 text-purple-400" />
        <p className="text-lg font-medium text-white mb-1">Short: Cảnh & Tài nguyên</p>
        <p className="text-sm">Upload audio + SRT cho short trước (tab &quot;Short: Âm thanh&quot;)</p>
      </div>
    );
  }

  const scenesWithPrompt = scenes.filter(s => s.veo3_prompt).length;
  const scenesMissingPrompt = scenes.length - scenesWithPrompt;
  const scenesMissingAsset = scenes.filter(s => s.veo3_prompt && !s.asset_path).length;
  const scenesWithAsset = scenes.filter(s => s.asset_path).length;
  const pendingApproval = scenes.filter(s => s.status !== "approved").length;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[17px] font-bold text-gray-800">
          Short: Cảnh & Tài nguyên {scenes.length > 0 && `(${scenes.length} cảnh)`}
        </h2>
        <button onClick={handleGenerate} disabled={generating}
          className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold rounded-xl bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 transition-colors shadow-sm">
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <List className="w-4 h-4" />}
          {generating ? "Đang chia cảnh..." : "Tạo từ SRT"}
        </button>
      </div>

      {/* Action buttons */}
      {scenes.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {/* Prompt buttons */}
          {scenesMissingPrompt > 0 && (
            <button onClick={() => handleGenerateAllPrompts('missing')} disabled={promptingAll || promptingScenes.size > 0}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 transition-colors shadow-sm">
              {promptingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Palette className="w-3.5 h-3.5" />}
              Tạo prompt ({scenesMissingPrompt})
            </button>
          )}
          {scenesWithPrompt > 0 && (
            <button onClick={() => handleGenerateAllPrompts('all')} disabled={promptingAll || promptingScenes.size > 0}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50 transition-colors shadow-sm">
              <Palette className="w-3.5 h-3.5" /> Tạo lại tất cả prompt
            </button>
          )}

          {scenesWithPrompt > 0 && <div className="w-px h-6 bg-gray-200" />}

          {/* Asset buttons */}
          {scenesMissingAsset > 0 && (
            <button onClick={() => handleGenerateAllAssets('missing')} disabled={generatingAssets || promptingAll}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-teal-500 text-white hover:bg-teal-600 disabled:opacity-50 transition-colors shadow-sm">
              {generatingAssets ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Image className="w-3.5 h-3.5" />}
              Tạo ảnh/video ({scenesMissingAsset})
            </button>
          )}
          {scenesWithAsset > 0 && (
            <button onClick={() => handleGenerateAllAssets('all')} disabled={generatingAssets || promptingAll}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50 transition-colors shadow-sm">
              <Image className="w-3.5 h-3.5" /> Tạo lại tất cả ảnh/video
            </button>
          )}

          {pendingApproval > 0 && <div className="w-px h-6 bg-gray-200" />}

          {pendingApproval > 0 && scenesWithAsset > 0 && (
            <button onClick={() => scenes.forEach(s => { if (s.status !== "approved") handleApprove(s.scene_number); })}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors shadow-sm">
              <CheckCircle2 className="w-3.5 h-3.5" /> Duyệt tất cả ({pendingApproval})
            </button>
          )}

          <div className="w-px h-6 bg-gray-200" />

          <button onClick={async () => {
            if (!confirm("Xóa tất cả phân đoạn short?")) return;
            try { await deleteAllShortScenes(projectId, videoId); await fetchScenes(); } catch { setError("Lỗi xóa phân đoạn."); }
          }} disabled={promptingAll || generatingAssets}
            className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors">
            <Trash2 className="w-3.5 h-3.5" /> Xóa ({scenes.length})
          </button>
        </div>
      )}

      {/* Prompt progress */}
      {(promptingAll || batchStatus) && (
        <div className="px-4 py-3 text-[12px] text-indigo-700 bg-indigo-50 rounded-xl mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
            <span>{batchStatus || "Đang xử lý..."}</span>
            {batchTotal > 0 && <span className="ml-auto font-bold">{batchDone}/{batchTotal} ({Math.round((batchDone / batchTotal) * 100)}%)</span>}
            {promptingAll && (
              <button onClick={handleStopPrompts} className="ml-2 px-3 py-1 text-[11px] font-semibold rounded-lg bg-rose-500 text-white hover:bg-rose-600 transition-colors">
                <X className="w-3 h-3 inline mr-1" />Dừng
              </button>
            )}
          </div>
          {batchTotal > 0 && (
            <div className="w-full bg-indigo-200 rounded-full h-2">
              <div className="bg-indigo-600 h-2 rounded-full transition-all duration-300" style={{ width: `${Math.round((batchDone / batchTotal) * 100)}%` }} />
            </div>
          )}
        </div>
      )}

      {/* Asset progress */}
      {(generatingAssets || assetStatus) && (
        <div className="px-4 py-3 text-[12px] text-teal-700 bg-teal-50 rounded-xl mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
            <span>{assetStatus || "Đang tạo ảnh/video..."}</span>
            {assetTotal > 0 && <span className="ml-auto font-bold">{assetDone}/{assetTotal} ({Math.round((assetDone / assetTotal) * 100)}%)</span>}
            {generatingAssets && (
              <button onClick={handleStopAssets} className="ml-2 px-3 py-1 text-[11px] font-semibold rounded-lg bg-rose-500 text-white hover:bg-rose-600 transition-colors">
                <X className="w-3 h-3 inline mr-1" />Dừng
              </button>
            )}
          </div>
          {assetTotal > 0 && (
            <div className="w-full bg-teal-200 rounded-full h-2">
              <div className="bg-teal-600 h-2 rounded-full transition-all duration-300" style={{ width: `${Math.round((assetDone / assetTotal) * 100)}%` }} />
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 text-[12px] text-rose-600 bg-rose-50 rounded-xl mb-4">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /> {error}
        </div>
      )}

      {(batchErrors.length > 0 || assetErrors.length > 0) && (
        <div className="px-4 py-3 text-[12px] text-amber-700 bg-amber-50 rounded-xl mb-4 space-y-1">
          {[...batchErrors, ...assetErrors].map((e, i) => (
            <div key={i} className="flex items-center gap-2"><AlertCircle className="w-3 h-3 flex-shrink-0" /> {e}</div>
          ))}
        </div>
      )}

      {/* Persistent error log */}
      {genErrorLog.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl mb-4 overflow-hidden">
          <button
            onClick={() => setShowErrorLog(!showErrorLog)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-[12px] font-semibold text-rose-700 hover:bg-rose-100 transition-colors"
          >
            <span className="flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5" />
              Lỗi tạo ảnh/video ({genErrorLog.length} lỗi)
            </span>
            <span className="flex items-center gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm("Xóa toàn bộ log lỗi?")) {
                    clearGenerationErrors(projectId, videoId).then(() => setGenErrorLog([]));
                  }
                }}
                className="px-2 py-0.5 text-[11px] rounded bg-rose-200 text-rose-700 hover:bg-rose-300 transition-colors"
              >
                Xóa log
              </button>
              <span className="text-rose-400">{showErrorLog ? "▲" : "▼"}</span>
            </span>
          </button>
          {showErrorLog && (
            <div className="px-4 pb-3 space-y-1.5 max-h-[300px] overflow-y-auto">
              {genErrorLog.map((err, i) => (
                <div key={i} className="flex items-start gap-2 text-[11px] text-rose-700 bg-white/60 rounded-lg px-3 py-2">
                  <span className="font-bold whitespace-nowrap">
                    Cảnh {err.scene_number} ({err.visual_type || err.type || "?"})
                  </span>
                  <span className="text-rose-500 flex-1 break-all">{err.error}</span>
                  <span className="text-rose-400 whitespace-nowrap text-[10px]">
                    {new Date(err.timestamp).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {scenes.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <List className="w-10 h-10 mx-auto mb-2 text-gray-300" />
          <p className="text-sm">Chưa có cảnh. Bấm &quot;Tạo từ SRT&quot; để bắt đầu.</p>
        </div>
      ) : (
        <SceneTimeline
          scenes={scenes}
          projectId={projectId}
          videoId={videoId}
          onApprove={handleApprove}
          onRedo={handleRedo}
          onClickScene={onClickScene}
          onGeneratePrompt={handleGeneratePrompt}
          promptingScenes={promptingScenes}
          onScenesUpdated={fetchScenes}
          onGenerateAssets={(sceneNumbers, visualTypeFilter) => handleGenerateSelectedAssets(sceneNumbers, visualTypeFilter)}
          generatingAssets={generatingAssets}
        />
      )}
    </div>
  );
}

function ShotlistTab({
  scenes,
  setScenes,
  projectId,
  videoId,
  onApprove,
  onRedo,
  onApproveAll,
  allScenesApproved,
  onClickScene,
  onScenesUpdated,
  onBuildCapcut,
  exportStatus,
}: {
  scenes: Scene[];
  setScenes: React.Dispatch<React.SetStateAction<Scene[]>>;
  projectId: string;
  videoId: string;
  onApprove: (n: number) => void;
  onRedo: (n: number) => void;
  onApproveAll: () => void;
  allScenesApproved: boolean;
  onClickScene: (scene: Scene) => void;
  onScenesUpdated: () => void;
  onBuildCapcut: () => void;
  exportStatus: string | null;
}) {
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [promptingScenes, setPromptingScenes] = useState<Set<number>>(new Set());
  const [promptingAll, setPromptingAll] = useState(false);
  const [batchStatus, setBatchStatus] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<string | null>(null);
  const [batchTotal, setBatchTotal] = useState(0);
  const [batchDone, setBatchDone] = useState(0);
  const [batchErrors, setBatchErrors] = useState<string[]>([]);
  // Asset generation state
  const [generatingAssets, setGeneratingAssets] = useState(false);
  const [assetStatus, setAssetStatus] = useState<string | null>(null);
  const [assetTotal, setAssetTotal] = useState(0);
  const [assetDone, setAssetDone] = useState(0);
  const [assetErrors, setAssetErrors] = useState<string[]>([]);
  const [generatingAssetScenes, setGeneratingAssetScenes] = useState<Set<number>>(new Set());
  // Persistent generation error log
  const [genErrorLog, setGenErrorLog] = useState<GenerationError[]>([]);
  const [showErrorLog, setShowErrorLog] = useState(false);
  // Abort controllers
  const promptAbortRef = useRef<AbortController | null>(null);
  const assetAbortRef = useRef<AbortController | null>(null);

  // Load persistent error log on mount
  useEffect(() => {
    getGenerationErrors(projectId, videoId).then(setGenErrorLog).catch(() => {});
  }, [projectId, videoId]);

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
        const updatedFields: Record<string, unknown> = {
          veo3_prompt: result.veo3_prompt,
          visual_type: (result.visual_type as "image" | "video") || "image",
          mood: result.mood || "",
        };
        if ((result as Record<string, unknown>).flow_characters) updatedFields.flow_characters = (result as Record<string, unknown>).flow_characters;
        await updateScene(projectId, videoId, sceneNumber, updatedFields);
        setScenes((prev) =>
          prev.map((s) =>
            s.scene_number === sceneNumber ? { ...s, ...updatedFields } : s
          )
        );
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
    const targetScenes = mode === 'all'
      ? scenes.map((s) => s.scene_number)
      : scenes.filter((s) => !s.veo3_prompt).map((s) => s.scene_number);

    const abortController = new AbortController();
    promptAbortRef.current = abortController;

    setPromptingAll(true);
    setGenError(null);
    setBatchStatus("Đang khởi tạo...");
    setBatchProgress(null);
    setBatchTotal(targetScenes.length);
    setBatchDone(0);
    setBatchErrors([]);
    setPromptingScenes(new Set(targetScenes));

    await streamGenerateAllPrompts(projectId, videoId, async (event: BatchPromptEvent) => {
      if (event.type === "status") {
        setBatchStatus(event.message || null);
      } else if (event.type === "plan_done") {
        setBatchStatus("Kế hoạch xong — đang tạo prompt song song...");
      } else if (event.type === "scene_done") {
        setBatchProgress(event.progress || null);
        setBatchDone((prev) => prev + 1);
        const sn = event.scene_number!;
        // Xóa scene khỏi danh sách đang xử lý
        setPromptingScenes((prev) => { const n = new Set(prev); n.delete(sn); return n; });

        if (event.status === "ok" && event.veo3_prompt) {
          const updatedFields: Record<string, unknown> = {
            veo3_prompt: event.veo3_prompt,
            visual_type: (event.visual_type as "image" | "video") || "image",
            mood: event.mood || "",
          };
          if (event.edit_plan) updatedFields.edit_plan = event.edit_plan;
          // Cập nhật state local (DB đã được chat_bridge lưu trước khi gửi SSE event)
          setScenes((prev) =>
            prev.map((s) =>
              s.scene_number === sn ? { ...s, ...updatedFields } : s
            )
          );
        } else {
          setBatchErrors((prev) => [...prev, `Cảnh ${sn}: ${event.message || "Lỗi"}`]);
        }
      } else if (event.type === "all_done" || event.type === "stopped") {
        setBatchStatus(event.type === "stopped" ? "Đã dừng — các cảnh hoàn thành đã được lưu" : null);
        setBatchProgress(null);
        setBatchTotal(0);
        setBatchDone(0);
        onScenesUpdated();
        getGenerationErrors(projectId, videoId).then(setGenErrorLog).catch(() => {});
        if (event.type === "stopped") setTimeout(() => setBatchStatus(null), 3000);
      } else if (event.type === "error") {
        setGenError(event.message || "Lỗi không xác định");
      }
    }, mode, abortController.signal);

    promptAbortRef.current = null;
    setPromptingAll(false);
    setPromptingScenes(new Set());
    if (abortController.signal.aborted) {
      setBatchStatus(null);
      onScenesUpdated();
    }
  };

  const handleStopPrompts = () => {
    cancelGeneration(projectId, videoId).catch(() => {});
    promptAbortRef.current?.abort();
    setBatchStatus("Đã dừng — các cảnh hoàn thành đã được lưu");
    setTimeout(() => setBatchStatus(null), 3000);
  };

  // Tạo ảnh/video cho nhiều cảnh (SSE stream)
  const handleGenerateAllAssets = async (mode: 'all' | 'missing' = 'missing', sceneNumbers?: number[], visualTypeFilter?: 'image' | 'video') => {
    const targetScenes = sceneNumbers
      ? sceneNumbers
      : mode === 'all'
        ? scenes.filter((s) => s.veo3_prompt).map((s) => s.scene_number)
        : scenes.filter((s) => s.veo3_prompt && !s.asset_path).map((s) => s.scene_number);

    const abortController = new AbortController();
    assetAbortRef.current = abortController;

    setGeneratingAssets(true);
    setGenError(null);
    setAssetStatus("Đang khởi tạo...");
    setAssetTotal(targetScenes.length);
    setAssetDone(0);
    setAssetErrors([]);
    setGeneratingAssetScenes(new Set(targetScenes));

    await streamGenerateSceneAssets(projectId, videoId, async (event: SceneAssetEvent) => {
      if (event.type === "status") {
        setAssetStatus(event.message || null);
      } else if (event.type === "scene_done") {
        setAssetDone((prev) => prev + 1);
        const sn = event.scene_number!;
        setGeneratingAssetScenes((prev) => { const n = new Set(prev); n.delete(sn); return n; });

        if (event.status === "ok" && event.asset_path) {
          setScenes((prev) =>
            prev.map((s) =>
              s.scene_number === sn
                ? { ...s, asset_path: event.asset_path!, asset_version: event.version, status: "review" }
                : s
            )
          );
        } else {
          setAssetErrors((prev) => [...prev, `Cảnh ${sn}: ${event.message || "Lỗi"}`]);
        }
      } else if (event.type === "all_done" || event.type === "stopped") {
        setAssetStatus(event.type === "stopped" ? "Đã dừng — các cảnh hoàn thành đã được lưu" : null);
        setAssetTotal(0);
        setAssetDone(0);
        onScenesUpdated();
        getGenerationErrors(projectId, videoId).then(setGenErrorLog).catch(() => {});
        if (event.type === "stopped") setTimeout(() => setAssetStatus(null), 3000);
      } else if (event.type === "error") {
        setGenError(event.message || "Lỗi không xác định");
      }
    }, mode, abortController.signal, sceneNumbers, visualTypeFilter);

    assetAbortRef.current = null;
    setGeneratingAssets(false);
    setGeneratingAssetScenes(new Set());
    if (abortController.signal.aborted) {
      setAssetStatus(null);
      onScenesUpdated();
    }
  };

  const handleStopAssets = () => {
    cancelGeneration(projectId, videoId).catch(() => {});
    assetAbortRef.current?.abort();
    setAssetStatus("Đã dừng — các cảnh hoàn thành đã được lưu");
    setTimeout(() => setAssetStatus(null), 3000);
  };

  const handleClearPrompts = async () => {
    if (!confirm("Xóa tất cả prompt đã tạo (bao gồm nhân vật gắn trong cảnh)? Bạn sẽ phải tạo lại từ đầu.")) return;
    try {
      await clearAllPrompts(projectId, videoId);
      await onScenesUpdated();
    } catch {
      setGenError("Lỗi xóa prompt.");
    }
  };

  const handleClearSceneCharacters = async () => {
    if (!confirm("Xóa nhân vật gắn trong tất cả cảnh?")) return;
    try {
      await clearSceneCharacters(projectId, videoId);
      await onScenesUpdated();
    } catch {
      setGenError("Lỗi xóa nhân vật trong cảnh.");
    }
  };

  const handleClearAssets = async () => {
    if (!confirm("Xóa tất cả ảnh/video đã tạo? Bạn sẽ phải tạo lại từ đầu.")) return;
    try {
      await clearAllAssets(projectId, videoId);
      await onScenesUpdated();
    } catch {
      setGenError("Lỗi xóa assets.");
    }
  };

  const scenesWithPrompt = scenes.filter((s) => s.veo3_prompt).length;
  const scenesMissingPrompt = scenes.length - scenesWithPrompt;
  const scenesMissingAsset = scenes.filter((s) => s.veo3_prompt && !s.asset_path).length;
  const scenesWithAsset = scenes.filter((s) => s.asset_path).length;
  const scenesWithCharacters = scenes.filter((s) => s.flow_characters && s.flow_characters.length > 0).length;
  const pendingApproval = scenes.filter((s) => s.status !== "approved").length;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[17px] font-bold text-gray-800">
          Cảnh & Tài nguyên {scenes.length > 0 && `(${scenes.length} cảnh)`}
        </h2>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-4 py-2 text-[13px] font-semibold rounded-xl bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 transition-colors shadow-sm"
        >
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <List className="w-4 h-4" />}
          {generating ? "Đang chia cảnh..." : "Tạo từ SRT"}
        </button>
      </div>

      {/* Action buttons row */}
      {scenes.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {/* Prompt buttons */}
          {scenesMissingPrompt > 0 && (
            <button
              onClick={() => handleGenerateAllPrompts('missing')}
              disabled={promptingAll || promptingScenes.size > 0}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {promptingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Palette className="w-3.5 h-3.5" />}
              Tạo prompt còn thiếu ({scenesMissingPrompt})
            </button>
          )}
          {scenesWithPrompt > 0 && (
            <button
              onClick={() => handleGenerateAllPrompts('all')}
              disabled={promptingAll || promptingScenes.size > 0}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {promptingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Palette className="w-3.5 h-3.5" />}
              Tạo lại tất cả prompt
            </button>
          )}

          {/* Divider */}
          {scenesWithPrompt > 0 && <div className="w-px h-6 bg-gray-200" />}

          {/* Asset buttons */}
          {scenesMissingAsset > 0 && (
            <button
              onClick={() => handleGenerateAllAssets('missing')}
              disabled={generatingAssets || promptingAll}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-teal-500 text-white hover:bg-teal-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {generatingAssets ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Grid3X3 className="w-3.5 h-3.5" />}
              Tạo ảnh/video còn thiếu ({scenesMissingAsset})
            </button>
          )}
          {scenesWithPrompt > 0 && (
            <button
              onClick={() => handleGenerateAllAssets('all')}
              disabled={generatingAssets || promptingAll}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {generatingAssets ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Grid3X3 className="w-3.5 h-3.5" />}
              Tạo lại tất cả ảnh/video
            </button>
          )}

          {/* Divider */}
          {pendingApproval > 0 && <div className="w-px h-6 bg-gray-200" />}

          {/* Approve all */}
          {!allScenesApproved && pendingApproval > 0 && (
            <button
              onClick={onApproveAll}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors shadow-sm"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Duyệt tất cả ({pendingApproval})
            </button>
          )}

          {/* Divider — Clear buttons */}
          <div className="w-px h-6 bg-gray-200" />

          {/* Xóa prompt */}
          {scenesWithPrompt > 0 && (
            <button
              onClick={handleClearPrompts}
              disabled={promptingAll || generatingAssets}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Xóa prompt ({scenesWithPrompt})
            </button>
          )}

          {/* Xóa nhân vật trong cảnh */}
          {scenesWithCharacters > 0 && (
            <button
              onClick={handleClearSceneCharacters}
              disabled={promptingAll || generatingAssets}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Xóa nhân vật ({scenesWithCharacters})
            </button>
          )}

          {/* Xóa assets */}
          {scenesWithAsset > 0 && (
            <button
              onClick={handleClearAssets}
              disabled={promptingAll || generatingAssets}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Xóa ảnh/video ({scenesWithAsset})
            </button>
          )}

          {/* Xóa phân đoạn */}
          <button
            onClick={async () => {
              if (!confirm("Xóa tất cả phân đoạn? Prompt và ảnh/video cũng sẽ bị xóa.")) return;
              try {
                await deleteAllScenes(projectId, videoId);
                await onScenesUpdated();
              } catch {
                setGenError("Lỗi xóa phân đoạn.");
              }
            }}
            disabled={promptingAll || generatingAssets}
            className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Xóa phân đoạn ({scenes.length})
          </button>

          {/* Divider */}
          {allScenesApproved && <div className="w-px h-6 bg-gray-200" />}

          {/* CapCut export */}
          {allScenesApproved && (
            <button
              onClick={onBuildCapcut}
              disabled={exportStatus === "building"}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-semibold rounded-lg bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {exportStatus === "building" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Package className="w-3.5 h-3.5" />}
              Tạo project CapCut
            </button>
          )}
        </div>
      )}

      {/* Export CapCut progress */}
      {exportStatus === "building" && (
        <div className="px-4 py-3 text-[12px] text-orange-700 bg-orange-50 rounded-xl mb-4">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
            <span>Đang tạo project CapCut...</span>
          </div>
        </div>
      )}

      {exportStatus === "error" && (
        <div className="flex items-center gap-2 px-4 py-3 text-[12px] text-rose-600 bg-rose-50 rounded-xl mb-4">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /> Tạo CapCut thất bại. Vui lòng thử lại.
        </div>
      )}

      {exportStatus?.startsWith("not_implemented") && (
        <div className="flex items-center gap-2 px-4 py-3 text-[12px] text-amber-600 bg-amber-50 rounded-xl mb-4">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /> {exportStatus.split(":")[1] || "Chức năng đang phát triển."}
        </div>
      )}

      {exportStatus && !exportStatus.startsWith("not_implemented") && exportStatus !== "building" && exportStatus !== "error" && (
        <div className="flex items-center gap-2 px-4 py-3 text-[12px] text-emerald-600 bg-emerald-50 rounded-xl mb-4">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> Xuất video thành công.
        </div>
      )}

      {/* Batch prompt status bar */}
      {(promptingAll || batchStatus) && (
        <div className="px-4 py-3 text-[12px] text-indigo-700 bg-indigo-50 rounded-xl mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
            <span>{batchStatus || "Đang xử lý..."}</span>
            {batchTotal > 0 && (
              <span className="ml-auto font-bold">
                {batchDone}/{batchTotal} cảnh ({Math.round((batchDone / batchTotal) * 100)}%)
              </span>
            )}
            {promptingAll && (
              <button
                onClick={handleStopPrompts}
                className="ml-2 px-3 py-1 text-[11px] font-semibold rounded-lg bg-rose-500 text-white hover:bg-rose-600 transition-colors"
              >
                <X className="w-3 h-3 inline mr-1" />Dừng lại
              </button>
            )}
          </div>
          {batchTotal > 0 && (
            <div className="w-full bg-indigo-200 rounded-full h-2">
              <div
                className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.round((batchDone / batchTotal) * 100)}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Asset generation progress bar */}
      {(generatingAssets || assetStatus) && (
        <div className="px-4 py-3 text-[12px] text-teal-700 bg-teal-50 rounded-xl mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
            <span>{assetStatus || "Đang tạo ảnh/video..."}</span>
            {assetTotal > 0 && (
              <span className="ml-auto font-bold">
                {assetDone}/{assetTotal} cảnh ({Math.round((assetDone / assetTotal) * 100)}%)
              </span>
            )}
            {generatingAssets && (
              <button
                onClick={handleStopAssets}
                className="ml-2 px-3 py-1 text-[11px] font-semibold rounded-lg bg-rose-500 text-white hover:bg-rose-600 transition-colors"
              >
                <X className="w-3 h-3 inline mr-1" />Dừng lại
              </button>
            )}
          </div>
          {assetTotal > 0 && (
            <div className="w-full bg-teal-200 rounded-full h-2">
              <div
                className="bg-teal-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.round((assetDone / assetTotal) * 100)}%` }}
              />
            </div>
          )}
        </div>
      )}

      {genError && (
        <div className="flex items-center gap-2 px-4 py-3 text-[12px] text-rose-600 bg-rose-50 rounded-xl mb-4">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /> {genError}
        </div>
      )}

      {(batchErrors.length > 0 || assetErrors.length > 0) && (
        <div className="px-4 py-3 text-[12px] text-amber-700 bg-amber-50 rounded-xl mb-4 space-y-1">
          {[...batchErrors, ...assetErrors].map((e, i) => (
            <div key={i} className="flex items-center gap-2">
              <AlertCircle className="w-3 h-3 flex-shrink-0" /> {e}
            </div>
          ))}
        </div>
      )}

      {/* Persistent error log */}
      {genErrorLog.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl mb-4 overflow-hidden">
          <button
            onClick={() => setShowErrorLog(!showErrorLog)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-[12px] font-semibold text-rose-700 hover:bg-rose-100 transition-colors"
          >
            <span className="flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5" />
              Lỗi tạo ảnh/video ({genErrorLog.length} lỗi)
            </span>
            <span className="flex items-center gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm("Xóa toàn bộ log lỗi?")) {
                    clearGenerationErrors(projectId, videoId).then(() => setGenErrorLog([]));
                  }
                }}
                className="px-2 py-0.5 text-[11px] rounded bg-rose-200 text-rose-700 hover:bg-rose-300 transition-colors"
              >
                Xóa log
              </button>
              <span className="text-rose-400">{showErrorLog ? "▲" : "▼"}</span>
            </span>
          </button>
          {showErrorLog && (
            <div className="px-4 pb-3 space-y-1.5 max-h-[300px] overflow-y-auto">
              {genErrorLog.map((err, i) => (
                <div key={i} className="flex items-start gap-2 text-[11px] text-rose-700 bg-white/60 rounded-lg px-3 py-2">
                  <span className="font-bold whitespace-nowrap">
                    Cảnh {err.scene_number} ({err.visual_type || err.type || "?"})
                  </span>
                  <span className="text-rose-500 flex-1 break-all">{err.error}</span>
                  <span className="text-rose-400 whitespace-nowrap text-[10px]">
                    {new Date(err.timestamp).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}
                  </span>
                </div>
              ))}
            </div>
          )}
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
          onScenesUpdated={onScenesUpdated}
          onGenerateAssets={(sceneNumbers, visualTypeFilter) => handleGenerateAllAssets('all', sceneNumbers, visualTypeFilter)}
          generatingAssets={generatingAssets}
        />
      )}
    </div>
  );
}
