"use client";

import { useState, useEffect } from "react";
import { Loader2, Save, Check, Film, Zap, Package, Clock, Volume2, Type, ArrowLeftRight } from "lucide-react";
import { getSettings, updateSettings } from "@/lib/api";
import type { AppSettings } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getSettings().then((s) => { setSettings(s); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setSaved(false);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-7 h-7 text-indigo-500 animate-spin" /></div>;
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight">Cài đặt</h1>
        <p className="text-[13px] text-gray-400 mt-1">Cấu hình hệ thống sản xuất video</p>
      </div>

      <div className="space-y-6">
        {/* Export Method */}
        <section className="bg-white rounded-2xl p-6">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center"><Film className="w-[18px] h-[18px] text-indigo-500" /></div>
            <h2 className="text-[15px] font-bold text-gray-800">Phương pháp xuất video</h2>
          </div>

          <div className="grid grid-cols-1 gap-3">
            <label
              onClick={() => setSettings({ ...settings, export_method: "ffmpeg" })}
              className={`relative flex gap-4 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                settings.export_method === "ffmpeg"
                  ? "border-indigo-500 bg-indigo-50/50"
                  : "border-gray-100 hover:border-gray-200"
              }`}
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                settings.export_method === "ffmpeg" ? "bg-indigo-100" : "bg-gray-50"
              }`}>
                <Zap className={`w-5 h-5 ${settings.export_method === "ffmpeg" ? "text-indigo-600" : "text-gray-400"}`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-[13px] font-bold text-gray-800">FFmpeg Auto-Render</h3>
                  <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">Khuyến nghị</span>
                </div>
                <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">
                  Tự động render ra MP4 hoàn chỉnh. Preview ngay trên web, không cần mở app nào.
                  Hỗ trợ Ken Burns, transitions, phụ đề burn-in, nhạc nền.
                </p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {["Tự động 100%", "Preview trên web", "Không cần CapCut", "Ổn định"].map((tag) => (
                    <span key={tag} className="text-[10px] text-indigo-500 bg-indigo-50 px-1.5 py-0.5 rounded font-medium">{tag}</span>
                  ))}
                </div>
              </div>
              {settings.export_method === "ffmpeg" && (
                <div className="absolute top-3 right-3"><Check className="w-5 h-5 text-indigo-500" /></div>
              )}
            </label>

            <label
              onClick={() => setSettings({ ...settings, export_method: "capcut" })}
              className={`relative flex gap-4 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                settings.export_method === "capcut"
                  ? "border-indigo-500 bg-indigo-50/50"
                  : "border-gray-100 hover:border-gray-200"
              }`}
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                settings.export_method === "capcut" ? "bg-indigo-100" : "bg-gray-50"
              }`}>
                <Package className={`w-5 h-5 ${settings.export_method === "capcut" ? "text-indigo-600" : "text-gray-400"}`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-[13px] font-bold text-gray-800">CapCut Package</h3>
                </div>
                <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">
                  Đóng gói assets + timing sheet. Mở CapCut Pro kéo vào chỉnh tay.
                  Phù hợp khi cần hiệu ứng phức tạp hoặc tinh chỉnh chi tiết.
                </p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {["Linh hoạt cao", "Hiệu ứng phức tạp", "Cần CapCut Pro", "Thủ công hơn"].map((tag) => (
                    <span key={tag} className="text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded font-medium">{tag}</span>
                  ))}
                </div>
              </div>
              {settings.export_method === "capcut" && (
                <div className="absolute top-3 right-3"><Check className="w-5 h-5 text-indigo-500" /></div>
              )}
            </label>
          </div>
        </section>

        {/* Veo 3 & Timing */}
        <section className="bg-white rounded-2xl p-6">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center"><Clock className="w-[18px] h-[18px] text-violet-500" /></div>
            <h2 className="text-[15px] font-bold text-gray-800">Veo 3 & Thời lượng</h2>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[12px] font-semibold text-gray-500 mb-1.5">Clip Veo 3 (giây)</label>
              <input type="number" min={1} max={30} value={settings.veo3_clip_duration}
                onChange={(e) => setSettings({ ...settings, veo3_clip_duration: parseInt(e.target.value) || 8 })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300" />
              <p className="text-[10px] text-gray-400 mt-1">Veo 3 mặc định tạo clip 8 giây</p>
            </div>
            <div>
              <label className="block text-[12px] font-semibold text-gray-500 mb-1.5">Độ dài video mặc định (phút)</label>
              <input type="number" min={1} max={60} value={settings.default_video_duration}
                onChange={(e) => setSettings({ ...settings, default_video_duration: parseInt(e.target.value) || 10 })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300" />
            </div>
          </div>
        </section>

        {/* Audio */}
        <section className="bg-white rounded-2xl p-6">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-lg bg-sky-50 flex items-center justify-center"><Volume2 className="w-[18px] h-[18px] text-sky-500" /></div>
            <h2 className="text-[15px] font-bold text-gray-800">Âm thanh</h2>
          </div>

          <div>
            <label className="block text-[12px] font-semibold text-gray-500 mb-1.5">Âm lượng nhạc nền (dB)</label>
            <input type="number" min={-30} max={0} value={settings.bgm_volume}
              onChange={(e) => setSettings({ ...settings, bgm_volume: parseInt(e.target.value) || -18 })}
              className="w-32 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300" />
            <p className="text-[10px] text-gray-400 mt-1">Khuyến nghị -18dB đến -22dB để không lấn át giọng đọc</p>
          </div>
        </section>

        {/* Transitions & Subtitles */}
        <section className="bg-white rounded-2xl p-6">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center"><ArrowLeftRight className="w-[18px] h-[18px] text-amber-500" /></div>
            <h2 className="text-[15px] font-bold text-gray-800">Chuyển cảnh & Phụ đề</h2>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[12px] font-semibold text-gray-500 mb-1.5">Kiểu chuyển cảnh</label>
              <select value={settings.transition_type}
                onChange={(e) => setSettings({ ...settings, transition_type: e.target.value as AppSettings["transition_type"] })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300">
                <option value="crossfade">Crossfade</option>
                <option value="fade_black">Fade to Black</option>
                <option value="cut">Cut thẳng</option>
              </select>
            </div>
            <div>
              <label className="block text-[12px] font-semibold text-gray-500 mb-1.5">Thời gian chuyển (giây)</label>
              <input type="number" min={0} max={3} step={0.1} value={settings.transition_duration}
                onChange={(e) => setSettings({ ...settings, transition_duration: parseFloat(e.target.value) || 0.5 })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300" />
            </div>
          </div>

          <div className="mt-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <div className={`w-10 h-6 rounded-full transition-colors relative ${settings.subtitle_burn_in ? "bg-indigo-500" : "bg-gray-200"}`}
                onClick={() => setSettings({ ...settings, subtitle_burn_in: !settings.subtitle_burn_in })}>
                <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${settings.subtitle_burn_in ? "translate-x-4" : "translate-x-0.5"}`} />
              </div>
              <div>
                <span className="text-[13px] font-medium text-gray-700">Burn-in phụ đề</span>
                <p className="text-[10px] text-gray-400">Ghi phụ đề trực tiếp vào video (FFmpeg)</p>
              </div>
            </label>
          </div>
        </section>

        {/* Save */}
        <div className="flex justify-end">
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-semibold rounded-xl bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 transition-colors shadow-sm">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
            {saved ? "Đã lưu" : "Lưu cài đặt"}
          </button>
        </div>
      </div>
    </div>
  );
}
