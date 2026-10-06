"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, Music, Loader2 } from "lucide-react";

interface AudioUploadProps {
  onUpload: (file: File) => Promise<void>;
  audioUrl?: string;
}

export function AudioUpload({ onUpload, audioUrl }: AudioUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [currentAudioUrl, setCurrentAudioUrl] = useState(audioUrl);
  const [uploadedName, setUploadedName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    setIsUploading(true);
    try {
      await onUpload(file);
      setCurrentAudioUrl(URL.createObjectURL(file));
      setUploadedName(file.name);
    } catch {
      // error handled by parent
    } finally {
      setIsUploading(false);
    }
  }, [onUpload]);

  return (
    <div className="space-y-4">
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*,.mp3,.wav,.m4a,.ogg,.aac,.flac"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }}
        className="hidden"
      />
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${isDragging ? "border-indigo-400 bg-indigo-50" : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"}`}
      >
        {isUploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            <p className="text-[13px] text-gray-500">Đang tải lên...</p>
          </div>
        ) : uploadedName ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center">
              <Music className="w-6 h-6 text-emerald-500" />
            </div>
            <p className="text-[13px] font-medium text-emerald-600">{uploadedName}</p>
            <p className="text-[12px] text-indigo-500 font-medium">Bấm hoặc kéo thả để thay file khác</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center">
              <Upload className="w-6 h-6 text-purple-500" />
            </div>
            <div>
              <p className="text-[13px] font-medium text-gray-600">Kéo thả file âm thanh hoặc bấm để chọn</p>
              <p className="text-[11px] text-gray-400 mt-1">MP3, WAV, M4A, OGG</p>
            </div>
          </div>
        )}
      </div>
      {currentAudioUrl && (
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-lg bg-purple-50 flex items-center justify-center"><Music className="w-4 h-4 text-purple-500" /></div>
            <p className="text-[13px] font-medium text-gray-600">Nghe thử</p>
          </div>
          <audio controls className="w-full" src={currentAudioUrl} />
        </div>
      )}
    </div>
  );
}
