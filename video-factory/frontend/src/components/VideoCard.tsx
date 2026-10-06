"use client";

import Link from "next/link";
import { Film } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import type { Video } from "@/lib/api";

interface VideoCardProps {
  video: Video;
  projectId: string;
}

export function VideoCard({ video, projectId }: VideoCardProps) {
  return (
    <Link href={`/projects/${projectId}/videos/${video.id}`}>
      <div className="bg-white rounded-2xl p-5 hover:shadow-md transition-all cursor-pointer group border border-transparent hover:border-gray-100">
        <div className="flex items-start justify-between mb-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
            <Film className="w-5 h-5 text-blue-500" />
          </div>
          <StatusBadge status={video.status} />
        </div>

        <h3 className="text-[14px] font-semibold text-gray-800 mb-2 group-hover:text-indigo-600 transition-colors">
          {video.title}
        </h3>

        {video.created_at && (
          <p className="text-[12px] text-gray-400">
            Ngày tạo {new Date(video.created_at).toLocaleDateString()}
          </p>
        )}
      </div>
    </Link>
  );
}
