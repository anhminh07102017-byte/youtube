"use client";

import { useState, useEffect } from "react";
import { Loader2, Palette, Scissors, Eye, ChevronDown, ChevronUp, Check, ArrowRight } from "lucide-react";
import { getTemplates, getProjects, getVideos, applyTemplateToProject, applyTemplateToVideo } from "@/lib/api";
import type { Template, Project, Video } from "@/lib/api";

function TemplateCard({ template }: { template: Template }) {
  const [showContent, setShowContent] = useState(false);
  const [showApply, setShowApply] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [selectedVideo, setSelectedVideo] = useState("");
  const [selectedTarget, setSelectedTarget] = useState("");
  const [applying, setApplying] = useState(false);
  const [success, setSuccess] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [loadingVideos, setLoadingVideos] = useState(false);

  const openApply = async () => {
    setShowApply(true); setSuccess(false); setSelectedProject(""); setSelectedVideo(""); setSelectedTarget(""); setLoadingProjects(true);
    try { setProjects(await getProjects()); } catch {} finally { setLoadingProjects(false); }
  };
  const handleProjectChange = async (pid: string) => {
    setSelectedProject(pid); setSelectedVideo(""); setVideos([]);
    if (pid && selectedTarget.includes("video")) { setLoadingVideos(true); try { setVideos(await getVideos(pid)); } catch {} finally { setLoadingVideos(false); } }
  };
  const handleTargetChange = async (target: string) => {
    setSelectedTarget(target); setSelectedVideo("");
    if (target.includes("video") && selectedProject) { setLoadingVideos(true); try { setVideos(await getVideos(selectedProject)); } catch {} finally { setLoadingVideos(false); } }
  };
  const needsVideo = selectedTarget.includes("video");
  const canApply = selectedProject && selectedTarget && (!needsVideo || selectedVideo);
  const handleApply = async () => {
    if (!canApply) return; setApplying(true);
    try { if (needsVideo) await applyTemplateToVideo(template.category, template.id, selectedProject, selectedVideo, selectedTarget); else await applyTemplateToProject(template.category, template.id, selectedProject, selectedTarget); setSuccess(true); } catch {} finally { setApplying(false); }
  };

  return (
    <div className="bg-white rounded-2xl p-5">
      <h3 className="text-[15px] font-bold text-gray-800">{template.name}</h3>
      <p className="text-[12px] text-gray-400 mt-1">{template.description}</p>
      <div className="bg-gray-50 rounded-xl p-3 mt-3 text-[12px] text-gray-500 whitespace-pre-line">{template.preview_summary}</div>

      <div className="flex items-center gap-2 mt-4">
        <button onClick={() => setShowContent(!showContent)} className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-semibold text-gray-500 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
          <Eye className="w-3.5 h-3.5" /> Chi tiết {showContent ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
        <button onClick={() => (showApply ? setShowApply(false) : openApply())} className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-semibold text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 transition-colors shadow-sm">
          <ArrowRight className="w-3.5 h-3.5" /> {showApply ? "Thu gọn" : "Áp dụng"}
        </button>
      </div>

      {showContent && <div className="mt-3 bg-gray-50 p-3 rounded-xl overflow-x-auto"><pre className="text-[12px] text-gray-500 font-mono whitespace-pre-wrap">{template.content}</pre></div>}

      {showApply && (
        <div className="bg-indigo-50/50 rounded-xl p-4 mt-3">
          {loadingProjects ? <div className="flex items-center gap-2 text-gray-400 text-[12px]"><Loader2 className="w-4 h-4 animate-spin text-indigo-500" /> Đang tải...</div> : (
            <>
              <label className="block text-[12px] font-semibold text-gray-600 mb-1.5">Chọn dự án:</label>
              <select value={selectedProject} onChange={(e) => handleProjectChange(e.target.value)} className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-[12px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300">
                <option value="">-- Chọn --</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>

              {selectedProject && (
                <div className="mt-3">
                  <label className="block text-[12px] font-semibold text-gray-600 mb-1.5">Áp dụng vào:</label>
                  <div className="space-y-1.5">
                    {template.applies_to.includes("project_style_guide") && <label className="flex items-center gap-2 text-[12px] text-gray-500 cursor-pointer"><input type="radio" name={`t-${template.id}`} value="project_style_guide" checked={selectedTarget === "project_style_guide"} onChange={(e) => handleTargetChange(e.target.value)} className="text-indigo-500" /> Hình ảnh (dự án)</label>}
                    {template.applies_to.includes("video_visual_guide") && <label className="flex items-center gap-2 text-[12px] text-gray-500 cursor-pointer"><input type="radio" name={`t-${template.id}`} value="video_visual_guide" checked={selectedTarget === "video_visual_guide"} onChange={(e) => handleTargetChange(e.target.value)} className="text-indigo-500" /> Hình ảnh (video)</label>}
                    {template.applies_to.includes("video_edit_guide") && <label className="flex items-center gap-2 text-[12px] text-gray-500 cursor-pointer"><input type="radio" name={`t-${template.id}`} value="video_edit_guide" checked={selectedTarget === "video_edit_guide"} onChange={(e) => handleTargetChange(e.target.value)} className="text-indigo-500" /> Hướng dẫn edit (video)</label>}
                  </div>
                </div>
              )}

              {needsVideo && selectedProject && (
                <div className="mt-3">
                  <label className="block text-[12px] font-semibold text-gray-600 mb-1.5">Chọn video:</label>
                  {loadingVideos ? <div className="text-[12px] text-gray-400"><Loader2 className="w-4 h-4 animate-spin text-indigo-500 inline mr-1" /> Đang tải...</div>
                    : <select value={selectedVideo} onChange={(e) => setSelectedVideo(e.target.value)} className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-[12px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300">
                      <option value="">-- Chọn --</option>
                      {videos.map((v) => <option key={v.id} value={v.id}>{v.title}</option>)}
                    </select>}
                </div>
              )}

              {success ? <div className="mt-3 flex items-center gap-1.5 text-emerald-600 text-[12px] font-semibold"><Check className="w-4 h-4" /> Đã áp dụng!</div>
                : <div className="flex items-center gap-2 mt-3">
                  <button onClick={handleApply} disabled={!canApply || applying} className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-semibold text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm">
                    {applying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} Áp dụng
                  </button>
                  <button onClick={() => setShowApply(false)} className="px-3 py-2 text-[12px] font-medium text-gray-400 hover:text-gray-600">Hủy</button>
                </div>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function TemplatesPage() {
  const [imageStyles, setImageStyles] = useState<Template[]>([]);
  const [editStyles, setEditStyles] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const f = async () => { try { setLoading(true); const d = await getTemplates(); setImageStyles(d.image_styles); setEditStyles(d.edit_styles); setError(null); } catch { setError("Không thể tải tài nguyên."); } finally { setLoading(false); } };
    f();
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight">Tài nguyên</h1>
        <p className="text-[13px] text-gray-400 mt-1">Thư viện template và tài nguyên dùng chung</p>
      </div>

      {loading ? <div className="flex items-center justify-center py-20"><Loader2 className="w-7 h-7 text-indigo-500 animate-spin" /></div>
        : error ? <div className="bg-rose-50 rounded-2xl p-6 text-center"><p className="text-[13px] text-rose-500">{error}</p></div>
        : imageStyles.length === 0 && editStyles.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center">
            <div className="w-14 h-14 rounded-2xl bg-violet-50 flex items-center justify-center mx-auto mb-4"><Palette className="w-7 h-7 text-violet-500" /></div>
            <h3 className="text-[15px] font-semibold text-gray-600">Chưa có tài nguyên nào.</h3>
          </div>
        ) : (
          <div className="space-y-8">
            {imageStyles.length > 0 && (
              <section>
                <div className="flex items-center gap-2.5 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center"><Palette className="w-[18px] h-[18px] text-violet-500" /></div>
                  <h2 className="text-[17px] font-bold text-gray-800">Phong cách hình ảnh</h2>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">{imageStyles.map((t) => <TemplateCard key={t.id} template={t} />)}</div>
              </section>
            )}
            {editStyles.length > 0 && (
              <section>
                <div className="flex items-center gap-2.5 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center"><Scissors className="w-[18px] h-[18px] text-amber-500" /></div>
                  <h2 className="text-[17px] font-bold text-gray-800">Phong cách edit</h2>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">{editStyles.map((t) => <TemplateCard key={t.id} template={t} />)}</div>
              </section>
            )}
          </div>
        )}
    </div>
  );
}
