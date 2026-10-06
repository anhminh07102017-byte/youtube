import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Minh Bi Youtube",
  description: "Hệ thống quản lý sản xuất video hoạt hình lịch sử",
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
          <main className="flex-1 ml-60 p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
