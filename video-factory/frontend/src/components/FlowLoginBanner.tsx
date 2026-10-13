"use client";

import { useState } from "react";
import { Loader2, Link as LinkIcon, ExternalLink } from "lucide-react";
import { flowLogin, flowStatus } from "@/lib/api";

interface FlowLoginBannerProps {
  onStatusChange?: (loggedIn: boolean) => void;
}

export function FlowLoginBanner({ onStatusChange }: FlowLoginBannerProps) {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);

  const handleOpenFlow = async () => {
    setChecking(true);
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
      setChecking(false);
    }
  };

  const handleCheckStatus = async () => {
    setChecking(true);
    try {
      const s = await flowStatus();
      setLoggedIn(s.logged_in);
      onStatusChange?.(s.logged_in);
    } catch {
      setLoggedIn(null);
    } finally {
      setChecking(false);
    }
  };

  if (loggedIn === true) {
    return (
      <div className="bg-emerald-50 rounded-2xl p-3 mb-4 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        <span className="text-[12px] text-emerald-600">Đã đăng nhập Google Flow</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 rounded-2xl p-3 mb-4 flex items-center gap-3">
      <span className="text-[12px] text-gray-500">Google Flow</span>
      <button
        onClick={handleOpenFlow}
        disabled={checking}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500 text-white text-[12px] font-semibold rounded-lg hover:bg-indigo-600 disabled:opacity-50 ml-auto whitespace-nowrap transition-colors"
      >
        {checking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ExternalLink className="w-3.5 h-3.5" />}
        Mở Flow
      </button>
      {loggedIn === false && (
        <button
          onClick={handleCheckStatus}
          disabled={checking}
          className="text-[11px] text-gray-400 hover:text-gray-600 underline whitespace-nowrap"
        >
          Kiểm tra lại
        </button>
      )}
    </div>
  );
}

export { flowLogin, flowStatus };
