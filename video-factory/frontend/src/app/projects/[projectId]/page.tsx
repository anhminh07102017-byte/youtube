"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Plus, Loader2, ArrowLeft, Film, FileText, Palette, BookOpen, Link as LinkIcon, Save, Settings } from "lucide-react";
import { VideoCard } from "@/components/VideoCard";
import { CreateVideoModal } from "@/components/CreateVideoModal";
import { GuideEditor } from "@/components/GuideEditor";
import { getProject, getVideos, createVideo, updateProject, getProjectGuide, updateProjectGuide } from "@/lib/api";
import type { Project, Video, CreateVideoData } from "@/lib/api";

type Tab = "videos" | "content_guide" | "style_guide";
const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "videos", label: "Video", icon: Film },
  { id: "content_guide", label: "Nội dung", icon: FileText },
  { id: "style_guide", label: "Hình ảnh", icon: Palette },
];

function FlowProjectIdField({ projectId, initialValue, onSaved }: { projectId: string; initialValue: string; onSaved: (val: string) => void }) {
  const [value, setValue] = useState(initialValue);
  const [saving, setSaving] = useState(false);
  const changed = value !== initialValue;
  const handleSave = async () => {
    setSaving(true);
    try { await updateProject(projectId, { flow_project_id: value }); onSaved(value); } catch {} finally { setSaving(false); }
  };
  return (
    <div className="mt-3 pt-3 border-t border-gray-50 flex items-center gap-3">
      <Settings className="w-4 h-4 text-gray-400 flex-shrink-0" />
      <span className="text-[12px] text-gray-400 whitespace-nowrap">Flow Project ID</span>
      <input
        type="text" value={value} onChange={(e) => setValue(e.target.value)}
        placeholder="VD: a86abc69-5508-4d56-931e-e587312105f2"
        className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-[12px] text-gray-700 bg-white placeholder-gray-300"
      />
      {changed && (
        <button onClick={handleSave} disabled={saving} className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500 text-white text-[11px] font-medium rounded-lg hover:bg-indigo-600 disabled:opacity-50">
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />} Lưu
        </button>
      )}
    </div>
  );
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<Project | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("videos");
  const [contentGuide, setContentGuide] = useState<{ content: string; exists: boolean; updated_at: string | null } | null>(null);
  const [styleGuide, setStyleGuide] = useState<{ content: string; exists: boolean; updated_at: string | null } | null>(null);
  const [guideLoading, setGuideLoading] = useState(false);

  const fetchData = async () => {
    try { setLoading(true); const [p, v] = await Promise.all([getProject(projectId), getVideos(projectId)]); setProject(p); setVideos(v); setError(null); }
    catch { setError("Không thể tải dữ liệu dự án."); } finally { setLoading(false); }
  };
  useEffect(() => { fetchData(); }, [projectId]);

  const handleCreateVideo = async (data: CreateVideoData) => { await createVideo(projectId, data); await fetchData(); };
  const fetchGuide = async (name: "content_guide" | "style_guide") => {
    setGuideLoading(true);
    try { const data = await getProjectGuide(projectId, name); if (name === "content_guide") setContentGuide(data); else setStyleGuide(data); } catch {} finally { setGuideLoading(false); }
  };
  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    if (tab === "content_guide" && !contentGuide) fetchGuide("content_guide");
    else if (tab === "style_guide" && !styleGuide) fetchGuide("style_guide");
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-7 h-7 text-indigo-500 animate-spin" /></div>;
  if (error || !project) return (
    <div className="bg-rose-50 rounded-2xl p-6 text-center">
      <p className="text-[13px] text-rose-500 font-medium">{error || "Không tìm thấy dự án"}</p>
      <Link href="/" className="mt-3 inline-block text-[12px] text-rose-400 hover:text-rose-600 underline">Quay lại</Link>
    </div>
  );

  return (
    <div>
      <Link href="/" className="inline-flex items-center gap-2 text-[13px] text-gray-400 hover:text-indigo-500 mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Quay lại bảng điều khiển
      </Link>

      <div className="bg-white rounded-2xl p-6 mb-6">
        <h1 className="text-xl font-bold text-gray-800 mb-3">{project.name}</h1>
        {project.sources && project.sources.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center gap-2 text-[12px] text-gray-400 mb-2">
              <BookOpen className="w-4 h-4" /> <span>Nguồn tham khảo ({project.sources.length})</span>
            </div>
            <div className="space-y-1">
              {project.sources.map((source, i) => {
                const hasLink = source.includes("|||");
                const title = hasLink ? source.split("|||")[0] : source;
                const url = hasLink ? source.split("|||")[1] : (source.startsWith("http") ? source : "");
                return (
                  <div key={i} className="flex items-center gap-2 text-[12px]">
                    <LinkIcon className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                    {url ? <a href={url} target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:text-indigo-700 truncate">{title}</a>
                      : <span className="text-gray-500 truncate">{title}</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {project.notes && <div className="mt-3 pt-3 border-t border-gray-50"><p className="text-[13px] text-gray-400">{project.notes}</p></div>}
        <FlowProjectIdField projectId={projectId} initialValue={project.flow_project_id || ""} onSaved={(val) => setProject((p) => p ? { ...p, flow_project_id: val } : p)} />
      </div>

      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} onClick={() => handleTabChange(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-[13px] font-medium border-b-2 transition-colors ${activeTab === tab.id ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-400 hover:text-gray-600"}`}>
                <Icon className="w-4 h-4" /> {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {activeTab === "videos" && (
        <>
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-[17px] font-bold text-gray-800">Video</h2>
            <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2 px-4 py-2 bg-indigo-500 text-white text-[13px] font-semibold rounded-xl hover:bg-indigo-600 transition-colors shadow-sm">
              <Plus className="w-4 h-4" /> Tạo video
            </button>
          </div>
          {videos.length === 0 ? (
            <div className="bg-white rounded-2xl p-12 text-center">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center mx-auto mb-4"><Film className="w-7 h-7 text-blue-500" /></div>
              <h3 className="text-[15px] font-semibold text-gray-700 mb-1">Chưa có video nào</h3>
              <p className="text-[13px] text-gray-400 mb-5">Tạo video đầu tiên</p>
              <button onClick={() => setShowCreateModal(true)} className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-500 text-white text-[13px] font-semibold rounded-xl hover:bg-indigo-600 transition-colors shadow-sm">
                <Plus className="w-4 h-4" /> Tạo video
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">{videos.map((v) => <VideoCard key={v.id} video={v} projectId={projectId} />)}</div>
          )}
        </>
      )}

      {activeTab === "content_guide" && (
        guideLoading && !contentGuide ? <div className="flex items-center justify-center py-20"><Loader2 className="w-7 h-7 text-indigo-500 animate-spin" /></div>
        : contentGuide ? <GuideEditor content={contentGuide.content} exists={contentGuide.exists} updatedAt={contentGuide.updated_at}
            onSave={async (c) => { await updateProjectGuide(projectId, "content_guide", c); setContentGuide(await getProjectGuide(projectId, "content_guide")); }}
            placeholder="Nhập quy định nội dung..." emptyMessage="Chưa có quy định nội dung. Tạo mới để AI tham chiếu khi viết kịch bản." /> : null
      )}

      {activeTab === "style_guide" && (
        guideLoading && !styleGuide ? <div className="flex items-center justify-center py-20"><Loader2 className="w-7 h-7 text-indigo-500 animate-spin" /></div>
        : styleGuide ? <GuideEditor content={styleGuide.content} exists={styleGuide.exists} updatedAt={styleGuide.updated_at}
            onSave={async (c) => { await updateProjectGuide(projectId, "style_guide", c); setStyleGuide(await getProjectGuide(projectId, "style_guide")); }}
            placeholder="Nhập quy định hình ảnh..." emptyMessage="Chưa có quy định hình ảnh. Tạo mới để AI tham chiếu khi tạo prompt." /> : null
      )}

      {showCreateModal && <CreateVideoModal onClose={() => setShowCreateModal(false)} onSubmit={handleCreateVideo} />}
    </div>
  );
}
