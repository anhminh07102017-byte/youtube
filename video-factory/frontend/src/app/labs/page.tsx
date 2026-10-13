"use client";

import Link from "next/link";
import { BookOpen, Palette, ArrowRight } from "lucide-react";

const labs = [
  {
    href: "/labs/storytelling",
    title: "Kể chuyện",
    description:
      "Phân tích cách dẫn chuyện từ video/kênh YouTube khác. Tạo storytelling profile để áp dụng vào project.",
    icon: BookOpen,
    color: "violet",
    examples: [
      "Gửi transcript video để phân tích cấu trúc narrative",
      "Mô tả cách hook, build-up, climax của kênh yêu thích",
      "Tổng hợp nhiều nguồn thành 1 cách kể chuyện nhất quán",
    ],
  },
  {
    href: "/labs/styles",
    title: "Phong cách",
    description:
      "Phân tích phong cách hình ảnh và cách edit video. Tạo template image style & edit style.",
    icon: Palette,
    color: "pink",
    examples: [
      "Mô tả color palette, art style, composition của video mẫu",
      "Phân tích transitions, pacing, text overlay, sound design",
      "Tạo template phong cách mới từ nhiều nguồn tham khảo",
    ],
  },
];

export default function LabsPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800">Phong lab</h1>
        <p className="text-[14px] text-gray-400 mt-1">
          Nghiên cứu và phân tích từ video/kênh khác — tạo profile & template
          áp dụng vào project.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {labs.map((lab) => {
          const Icon = lab.icon;
          return (
            <Link
              key={lab.href}
              href={lab.href}
              className="group block bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-lg hover:border-gray-200 transition-all"
            >
              <div className="flex items-start gap-4">
                <div
                  className={`w-12 h-12 rounded-xl bg-${lab.color}-50 flex items-center justify-center flex-shrink-0`}
                >
                  <Icon className={`w-6 h-6 text-${lab.color}-500`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h2 className="text-[16px] font-bold text-gray-800">
                      {lab.title}
                    </h2>
                    <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 group-hover:translate-x-1 transition-all" />
                  </div>
                  <p className="text-[13px] text-gray-500 mt-1">
                    {lab.description}
                  </p>
                  <div className="mt-4 space-y-1.5">
                    {lab.examples.map((ex, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 text-[12px] text-gray-400"
                      >
                        <span className={`w-1.5 h-1.5 rounded-full bg-${lab.color}-300 mt-1.5 flex-shrink-0`} />
                        {ex}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
