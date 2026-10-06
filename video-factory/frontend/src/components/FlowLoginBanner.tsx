"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, Link as LinkIcon } from "lucide-react";
import { flowLogin, flowStatus } from "@/lib/api";

interface FlowLoginBannerProps {
  onStatusChange?: (loggedIn: boolean) => void;
}

export function FlowLoginBanner({ onStatusChange }: FlowLoginBannerProps) {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  const checkLogin = useCallback(async () => {
    try {
      const s = await flowStatus();
      setLoggedIn(s.logged_in);
      onStatusChange?.(s.logged_in);
    } catch {
      setLoggedIn(null);
    }
  }, [onStatusChange]);

  useEffect(() => {
    checkLogin();
  }, [checkLogin]);

  const handleLogin = async () => {
    setLoggingIn(true);
    try {
      const result = await flowLogin();
      setLoggedIn(result.logged_in);
      onStatusChange?.(result.logged_in);
      if (!result.logged_in) {
        alert(result.message);
      }
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Không mở được trình duyệt Flow.");
    } finally {
      setLoggingIn(false);
    }
  };

  if (loggedIn === null) return null;

  if (loggedIn === false) {
    return (
      <div className="bg-amber-50 rounded-2xl p-4 mb-4 flex items-center gap-3">
        <span className="text-[13px] text-amber-700">Chưa đăng nhập Google Flow. Cần đăng nhập để tạo ảnh/video.</span>
        <button
          onClick={handleLogin}
          disabled={loggingIn}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white text-[13px] font-semibold rounded-xl hover:bg-amber-600 disabled:opacity-50 ml-auto whitespace-nowrap"
        >
          {loggingIn ? <Loader2 className="w-4 h-4 animate-spin" /> : <LinkIcon className="w-4 h-4" />}
          Đăng nhập Flow
        </button>
        <button
          onClick={checkLogin}
          className="text-[12px] text-amber-600 hover:text-amber-800 underline whitespace-nowrap"
        >
          Kiểm tra lại
        </button>
      </div>
    );
  }

  return (
    <div className="bg-emerald-50 rounded-2xl p-3 mb-4 flex items-center gap-2">
      <span className="w-2 h-2 rounded-full bg-emerald-500" />
      <span className="text-[12px] text-emerald-600">Đã đăng nhập Google Flow</span>
    </div>
  );
}

export { flowLogin, flowStatus };
