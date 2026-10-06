"use client";

import { useState, useEffect } from "react";
import { Plus, Loader2, FolderOpen } from "lucide-react";
import { ProjectCard } from "@/components/ProjectCard";
import { CreateProjectModal } from "@/components/CreateProjectModal";
import { getProjects, createProject } from "@/lib/api";
import type { Project, CreateProjectData } from "@/lib/api";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await getProjects();
      setProjects(data);
      setError(null);
    } catch (err) {
      setError("Không thể tải dự án. Backend có đang chạy không?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = async (data: CreateProjectData) => {
    await createProject(data);
    await fetchProjects();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 tracking-tight">Bảng điều khiển</h1>
          <p className="text-[13px] text-gray-400 mt-1">Quản lý các dự án sản xuất video</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-500 text-white text-[13px] font-semibold rounded-xl hover:bg-indigo-600 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Tạo dự án
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-7 h-7 text-indigo-500 animate-spin" />
        </div>
      ) : error ? (
        <div className="bg-rose-50 rounded-2xl p-6 text-center">
          <p className="text-[13px] text-rose-500 font-medium">{error}</p>
          <button onClick={fetchProjects} className="mt-3 text-[12px] text-rose-400 hover:text-rose-600 underline">
            Thử lại
          </button>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-50 flex items-center justify-center mx-auto mb-4">
            <FolderOpen className="w-7 h-7 text-amber-500" />
          </div>
          <h3 className="text-[15px] font-semibold text-gray-700 mb-1">Chưa có dự án nào</h3>
          <p className="text-[13px] text-gray-400 mb-5">Tạo dự án đầu tiên để bắt đầu</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-500 text-white text-[13px] font-semibold rounded-xl hover:bg-indigo-600 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Tạo dự án
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateProject}
        />
      )}
    </div>
  );
}
