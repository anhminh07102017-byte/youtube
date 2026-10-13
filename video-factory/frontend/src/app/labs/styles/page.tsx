"use client";

import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { LabChatPanel } from "@/components/LabChatPanel";

export default function StylesLabPage() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/labs"
          className="p-2 rounded-lg bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-gray-800">
            Lab Phong cách
          </h1>
          <p className="text-[12px] text-gray-400">
            Phân tích hình ảnh & edit — tạo image style / edit style template
          </p>
        </div>
      </div>
      <LabChatPanel labType="styles" />
    </div>
  );
}
