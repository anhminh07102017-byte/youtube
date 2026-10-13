import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Minh Bi Youtube — Hệ thống tạo video tự động",
  description:
    "Hệ thống tạo video hoàn toàn tự động — từ kịch bản, hình ảnh AI đến xuất video. Minh Bi Youtube.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "Minh Bi Youtube — Hệ thống tạo video tự động",
    description:
      "Tạo video lịch sử hoạt hình 2D hoàn toàn tự động với AI. Kịch bản, hình ảnh, dựng phim — một hệ thống duy nhất.",
    siteName: "Minh Bi Youtube",
    locale: "vi_VN",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-16 lg:ml-60 p-4 lg:p-8 overflow-x-hidden">{children}</main>
        </div>
      </body>
    </html>
  );
}
