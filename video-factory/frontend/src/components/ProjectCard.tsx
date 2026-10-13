"use client";

import Link from "next/link";
import { FolderOpen, Film, BookOpen } from "lucide-react";
import type { Project } from "@/lib/api";

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  const sourceCount = project.sources?.length || 0;

  return (
    <Link href={`/projects/${project.id}`}>
      <div className="bg-white rounded-2xl p-5 hover:shadow-md transition-all cursor-pointer group border border-transparent hover:border-gray-100">
        <div className="flex items-start justify-between mb-3">
          <div className="w-11 h-11 rounded-xl bg-amber-50 flex items-center justify-center">
            <FolderOpen className="w-5 h-5 text-amber-500" />
          </div>
          {project.era && (
            <span className="text-[11px] text-indigo-600 bg-indigo-50 px-2 py-1 rounded-lg font-semibold">
              {project.era}
            </span>
          )}
        </div>

        <h3 className="text-[15px] font-semibold text-gray-800 mb-1 group-hover:text-indigo-600 transition-colors">
          {project.name}
        </h3>

        {project.time_period && (
          <p className="text-[12px] text-gray-400">{project.time_period}</p>
        )}

        {project.notes && (
          <p className="text-[12px] text-gray-400 mt-1.5 line-clamp-2 leading-relaxed">{project.notes}</p>
        )}

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-50">
          <div className="flex items-center gap-1.5 text-[13px] text-gray-400">
            <Film className="w-4 h-4" />
            <span>{project.video_count ?? 0} video</span>
          </div>

          {sourceCount > 0 && (
            <div className="flex items-center gap-1 text-[11px] text-gray-400">
              <BookOpen className="w-3.5 h-3.5" />
              <span>{sourceCount} nguồn</span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
