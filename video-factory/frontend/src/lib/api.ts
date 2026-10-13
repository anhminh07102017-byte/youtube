const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Chuyển API path thành full URL cho img/video src */
export function assetUrl(path: string | undefined | null): string {
  if (!path) return '';
  return `${API_URL}${path}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}/api${path}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }
  return res.json();
}

async function requestFormData<T>(path: string, formData: FormData): Promise<T> {
  const url = `${API_URL}/api${path}`;
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }
  return res.json();
}

// ---- Types ----

export interface Project {
  id: string;
  name: string;
  type: string;
  era: string;
  time_period: string;
  sources: string[];
  notes: string;
  base_style?: string;
  video_count?: number;
  status_counts?: Record<string, number>;
  flow_project_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Video {
  id: string;
  project_id: string;
  title: string;
  status: string;
  target_duration?: number;
  srt_path?: string;
  audio_path?: string;
  flow_project_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Script {
  content: string;
  status: string;
  updated_at?: string;
}

export interface EditPlan {
  transition_in?: string;
  transition_out?: string;
  ken_burns?: string | null;
  pacing?: string;
  text_overlay?: string | null;
  sound_note?: string | null;
}

export interface Scene {
  scene_number: number;
  timestamp_start: number;
  timestamp_end: number;
  script_text?: string;
  veo3_prompt?: string;
  visual_type: 'image' | 'video';
  content_tag?: string;
  camera_movement?: string;
  effect?: string;
  mood?: string;
  text_overlay?: string;
  edit_plan?: EditPlan;
  flow_characters?: string[];
  status: string;
  asset_path?: string;
  asset_version?: number;
  asset_url?: string;
  versions?: SceneVersion[];
}

export interface SceneVersion {
  version: number;
  asset_url: string;
  created_at: string;
}

export interface Character {
  id: string;
  project_id: string;
  video_id?: string;
  name: string;
  historical_name?: string;
  era?: string;
  age_range?: string;
  reference_description?: string;
  visual_prompt_base: string;
  visual_variants?: Record<string, string>;
  color_palette?: Record<string, string>;
  consistency_anchors?: string[];
  reference_image_path?: string;
  flow_character_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateProjectData {
  id: string;
  name: string;
  sources: string[];
  notes: string;
}

export interface CreateVideoData {
  id: string;
  title: string;
  target_duration?: number; // minutes
}

// ---- Projects ----

export async function getProjects(): Promise<Project[]> {
  return request<Project[]>('/projects');
}

export async function createProject(data: CreateProjectData): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getProject(id: string): Promise<Project> {
  return request<Project>(`/projects/${id}`);
}

export async function updateProject(id: string, data: Partial<Project>): Promise<Project> {
  return request<Project>(`/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ---- Videos ----

export async function getVideos(projectId: string): Promise<Video[]> {
  return request<Video[]>(`/projects/${projectId}/videos`);
}

export async function createVideo(projectId: string, data: CreateVideoData): Promise<Video> {
  return request<Video>(`/projects/${projectId}/videos`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getVideo(projectId: string, videoId: string): Promise<Video> {
  return request<Video>(`/projects/${projectId}/videos/${videoId}`);
}

// ---- Script ----

export async function getScript(projectId: string, videoId: string): Promise<Script> {
  return request<Script>(`/projects/${projectId}/videos/${videoId}/script`);
}

export async function updateScript(projectId: string, videoId: string, content: string): Promise<Script> {
  return request<Script>(`/projects/${projectId}/videos/${videoId}/script`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

// ---- Audio ----

export async function uploadAudio(projectId: string, videoId: string, file: File): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append('file', file);
  return requestFormData<{ url: string }>(`/projects/${projectId}/videos/${videoId}/audio`, formData);
}

// ---- SRT ----

export async function uploadSrt(projectId: string, videoId: string, file: File): Promise<Video> {
  const formData = new FormData();
  formData.append('file', file);
  return requestFormData<Video>(`/projects/${projectId}/videos/${videoId}/srt`, formData);
}

export async function getSrt(projectId: string, videoId: string): Promise<{ content: string; exists: boolean }> {
  return request<{ content: string; exists: boolean }>(`/projects/${projectId}/videos/${videoId}/srt`);
}

export async function deleteSrt(projectId: string, videoId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/projects/${projectId}/videos/${videoId}/srt`, { method: 'DELETE' });
}

// ---- Scenes ----

export async function getScenes(projectId: string, videoId: string): Promise<Scene[]> {
  return request<Scene[]>(`/projects/${projectId}/videos/${videoId}/scenes`);
}

export async function updateScene(
  projectId: string,
  videoId: string,
  sceneNumber: number,
  data: Partial<Scene>,
  isShort: boolean = false
): Promise<Scene> {
  const qs = isShort ? '?is_short=true' : '';
  return request<Scene>(`/projects/${projectId}/videos/${videoId}/scenes/${sceneNumber}${qs}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function updateSceneStatus(
  projectId: string,
  videoId: string,
  sceneNumber: number,
  status: string,
  isShort: boolean = false
): Promise<Scene> {
  const qs = isShort ? '?is_short=true' : '';
  return request<Scene>(`/projects/${projectId}/videos/${videoId}/scenes/${sceneNumber}/status${qs}`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  });
}

export interface SceneBulkItem {
  scene_number: number;
  timestamp_start: number;
  timestamp_end: number;
  script_text: string;
  visual_type: string;
  content_tag?: string;
  mood?: string;
}

export async function bulkCreateScenes(projectId: string, videoId: string, scenes: SceneBulkItem[]): Promise<Scene[]> {
  return request<Scene[]>(`/projects/${projectId}/videos/${videoId}/scenes/bulk`, {
    method: 'POST',
    body: JSON.stringify({ scenes }),
  });
}

export async function mergeScenes(projectId: string, videoId: string, sceneNumbers: number[]): Promise<Scene[]> {
  return request<Scene[]>(`/projects/${projectId}/videos/${videoId}/scenes/merge`, {
    method: 'POST',
    body: JSON.stringify({ scene_numbers: sceneNumbers }),
  });
}

export async function batchClearPrompts(projectId: string, videoId: string, sceneNumbers: number[]): Promise<{ status: string; cleared: number }> {
  return request<{ status: string; cleared: number }>(`/projects/${projectId}/videos/${videoId}/scenes/batch-clear-prompts`, {
    method: 'POST',
    body: JSON.stringify({ scene_numbers: sceneNumbers }),
  });
}

export async function batchClearAssets(projectId: string, videoId: string, sceneNumbers: number[]): Promise<{ status: string; cleared: number }> {
  return request<{ status: string; cleared: number }>(`/projects/${projectId}/videos/${videoId}/scenes/batch-clear-assets`, {
    method: 'POST',
    body: JSON.stringify({ scene_numbers: sceneNumbers }),
  });
}

export async function deleteAllScenes(projectId: string, videoId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/projects/${projectId}/videos/${videoId}/scenes`, { method: 'DELETE' });
}

export async function clearAllPrompts(projectId: string, videoId: string): Promise<{ status: string; cleared: number }> {
  return request<{ status: string; cleared: number }>(`/projects/${projectId}/videos/${videoId}/scenes/prompts`, {
    method: 'DELETE',
  });
}

export async function clearAllAssets(projectId: string, videoId: string): Promise<{ status: string; cleared: number }> {
  return request<{ status: string; cleared: number }>(`/projects/${projectId}/videos/${videoId}/scenes/assets`, {
    method: 'DELETE',
  });
}

export async function clearCharacterImages(projectId: string, videoId: string): Promise<{ status: string; cleared: number }> {
  return request<{ status: string; cleared: number }>(`/projects/${projectId}/videos/${videoId}/characters/images`, {
    method: 'DELETE',
  });
}

export async function clearSceneCharacters(projectId: string, videoId: string): Promise<{ status: string; cleared: number }> {
  return request<{ status: string; cleared: number }>(`/projects/${projectId}/videos/${videoId}/scenes/characters`, {
    method: 'DELETE',
  });
}

export async function generateShotlist(projectId: string, videoId: string): Promise<{ status: string; scenes?: SceneBulkItem[]; message?: string }> {
  return chatRequest<{ status: string; scenes?: SceneBulkItem[]; message?: string }>(`/api/generate-shotlist/${projectId}/${videoId}`, {
    method: 'POST',
  });
}

export interface ScenePromptResult {
  status: string;
  scene_number?: number;
  veo3_prompt?: string;
  visual_type?: string;
  mood?: string;
  message?: string;
}

export async function generateScenePrompt(projectId: string, videoId: string, sceneNumber: number): Promise<ScenePromptResult> {
  return chatRequest<ScenePromptResult>(`/api/generate-scene-prompt/${projectId}/${videoId}/${sceneNumber}`, {
    method: 'POST',
  });
}

// ---- Characters ----

export async function getCharacters(projectId: string, videoId: string): Promise<Character[]> {
  return request<Character[]>(`/projects/${projectId}/videos/${videoId}/characters`);
}

export async function createCharacter(projectId: string, videoId: string, data: Omit<Character, 'id'>): Promise<Character> {
  return request<Character>(`/projects/${projectId}/videos/${videoId}/characters`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getCharacter(projectId: string, videoId: string, characterId: string): Promise<Character> {
  return request<Character>(`/projects/${projectId}/videos/${videoId}/characters/${characterId}`);
}

export async function updateCharacter(projectId: string, videoId: string, characterId: string, data: Partial<Character>): Promise<Character> {
  return request<Character>(`/projects/${projectId}/videos/${videoId}/characters/${characterId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteCharacter(projectId: string, videoId: string, characterId: string): Promise<void> {
  await request<void>(`/projects/${projectId}/videos/${videoId}/characters/${characterId}`, {
    method: 'DELETE',
  });
}

export async function extractCharacters(projectId: string, videoId: string): Promise<{ status: string; characters?: Omit<Character, 'id' | 'project_id' | 'video_id'>[]; message?: string }> {
  return chatRequest<{ status: string; characters?: Omit<Character, 'id' | 'project_id' | 'video_id'>[]; message?: string }>(`/api/extract-characters/${projectId}/${videoId}`, {
    method: 'POST',
  });
}

export async function flowLogin(): Promise<{ status: string; logged_in: boolean; message: string }> {
  return chatRequest<{ status: string; logged_in: boolean; message: string }>('/api/flow-login', { method: 'POST' });
}

export async function flowStatus(): Promise<{ logged_in: boolean }> {
  return chatRequest<{ logged_in: boolean }>('/api/flow-status');
}

export async function cancelGeneration(projectId: string, videoId: string): Promise<{ status: string }> {
  return chatRequest<{ status: string }>(`/api/cancel-generation/${projectId}/${videoId}`, { method: 'POST' });
}

export async function generateCharacterImage(projectId: string, videoId: string, characterId: string): Promise<{ status: string; image_path?: string; flow_character_id?: string; error?: string }> {
  return chatRequest<{ status: string; image_path?: string; flow_character_id?: string; error?: string }>(`/api/generate-character-image/${projectId}/${videoId}/${characterId}`, {
    method: 'POST',
  });
}

export async function generateAllCharacterImages(projectId: string, videoId: string): Promise<{ status: string; results: { id: string; name: string; status: string; image_path?: string; error?: string }[] }> {
  return chatRequest<{ status: string; results: { id: string; name: string; status: string; image_path?: string; error?: string }[] }>(`/api/generate-all-character-images/${projectId}/${videoId}`, {
    method: 'POST',
  });
}

export interface CharImageEvent {
  type: 'status' | 'char_done' | 'all_done' | 'stopped' | 'error';
  character_id?: string;
  name?: string;
  status?: string;
  image_path?: string;
  message?: string;
  progress?: string;
  total?: number;
}

export async function streamGenerateCharacterImages(
  projectId: string,
  videoId: string,
  onEvent: (event: CharImageEvent) => Promise<void> | void,
  mode: 'all' | 'missing' = 'missing',
  signal?: AbortSignal,
): Promise<void> {
  try {
    const resp = await fetch(`${CHAT_URL}/api/generate-all-character-images/${projectId}/${videoId}?mode=${mode}`, {
      method: 'POST',
      signal,
    });
    if (!resp.ok || !resp.body) throw new Error('SSE connection failed');
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            await onEvent(event);
          } catch { /* skip */ }
        }
      }
    }
  } catch (e) {
    if (signal?.aborted) return;
    throw e;
  }
}

export async function cancelCharacterGeneration(projectId: string, videoId: string): Promise<{ status: string }> {
  return chatRequest<{ status: string }>(`/api/cancel-character-generation/${projectId}/${videoId}`, {
    method: 'POST',
  });
}

// ---- Scene Asset Generation ----

export async function generateSceneAsset(projectId: string, videoId: string, sceneNumber: number): Promise<{ status: string; scene_number: number; asset_path?: string; version?: number }> {
  return chatRequest<{ status: string; scene_number: number; asset_path?: string; version?: number }>(`/api/generate-scene-asset/${projectId}/${videoId}/${sceneNumber}`, {
    method: 'POST',
  });
}

export interface SceneAssetEvent {
  type: 'status' | 'scene_done' | 'all_done' | 'error' | 'stopped';
  scene_number?: number;
  status?: string;
  message?: string;
  asset_path?: string;
  version?: number;
  progress?: string;
  total?: number;
}

export async function streamGenerateSceneAssets(
  projectId: string,
  videoId: string,
  onEvent: (event: SceneAssetEvent) => Promise<void> | void,
  mode: 'all' | 'missing' = 'missing',
  signal?: AbortSignal,
  sceneNumbers?: number[],
  visualTypeFilter?: 'image' | 'video',
): Promise<void> {
  const params = new URLSearchParams({ mode });
  if (sceneNumbers && sceneNumbers.length > 0) {
    params.set('scenes_filter', sceneNumbers.join(','));
  }
  if (visualTypeFilter) {
    params.set('visual_type_filter', visualTypeFilter);
  }
  const resp = await fetch(`${CHAT_URL}/api/generate-scene-assets/${projectId}/${videoId}?${params}`, {
    method: 'POST',
    signal,
  });
  if (!resp.ok || !resp.body) throw new Error('SSE connection failed');

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6)) as SceneAssetEvent;
            await onEvent(event);
          } catch { /* skip malformed */ }
        }
      }
    }
  } catch (e) {
    if (signal?.aborted) return; // Stopped by user
    throw e;
  }
}

// ---- Export ----

export async function buildCapcutProject(projectId: string, videoId: string): Promise<{ status: string; message?: string }> {
  return chatRequest<{ status: string; message?: string }>(`/api/build-capcut/${projectId}/${videoId}`, {
    method: 'POST',
  });
}

// ---- Guides ----

export async function getProjectGuide(projectId: string, guideName: string): Promise<{ content: string; exists: boolean; updated_at: string | null }> {
  return request<{ content: string; exists: boolean; updated_at: string | null }>(`/projects/${projectId}/guides/${guideName}`);
}

export async function updateProjectGuide(projectId: string, guideName: string, content: string): Promise<{ content: string; updated_at: string }> {
  return request<{ content: string; updated_at: string }>(`/projects/${projectId}/guides/${guideName}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

export async function getVideoGuide(projectId: string, videoId: string, guideName: string): Promise<{ content: string; exists: boolean; updated_at: string | null }> {
  return request<{ content: string; exists: boolean; updated_at: string | null }>(`/projects/${projectId}/videos/${videoId}/guides/${guideName}`);
}

export async function updateVideo(projectId: string, videoId: string, data: { flow_project_id?: string; title?: string; status?: string }): Promise<Video> {
  return request<Video>(`/projects/${projectId}/videos/${videoId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function updateVideoGuide(projectId: string, videoId: string, guideName: string, content: string): Promise<{ content: string; updated_at: string }> {
  return request<{ content: string; updated_at: string }>(`/projects/${projectId}/videos/${videoId}/guides/${guideName}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

// ---- Short (guides, audio, SRT, scenes, chat) ----

export async function getShortGuide(projectId: string, videoId: string, guideName: string): Promise<{ content: string; exists: boolean; updated_at: string | null }> {
  return request<{ content: string; exists: boolean; updated_at: string | null }>(`/projects/${projectId}/videos/${videoId}/short/guides/${guideName}`);
}

export async function updateShortGuide(projectId: string, videoId: string, guideName: string, content: string): Promise<{ content: string; updated_at: string }> {
  return request<{ content: string; updated_at: string }>(`/projects/${projectId}/videos/${videoId}/short/guides/${guideName}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

export async function uploadShortAudio(projectId: string, videoId: string, file: File): Promise<{ status: string }> {
  const formData = new FormData();
  formData.append('file', file);
  return requestFormData<{ status: string }>(`/projects/${projectId}/videos/${videoId}/short/audio`, formData);
}

export async function uploadShortSrt(projectId: string, videoId: string, file: File): Promise<{ status: string }> {
  const formData = new FormData();
  formData.append('file', file);
  return requestFormData<{ status: string }>(`/projects/${projectId}/videos/${videoId}/short/srt`, formData);
}

export async function getShortSrt(projectId: string, videoId: string): Promise<{ content: string; exists: boolean }> {
  return request<{ content: string; exists: boolean }>(`/projects/${projectId}/videos/${videoId}/short/srt`);
}

export async function deleteShortSrt(projectId: string, videoId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/projects/${projectId}/videos/${videoId}/short/srt`, { method: 'DELETE' });
}

export async function getShortScenes(projectId: string, videoId: string): Promise<Scene[]> {
  return request<Scene[]>(`/projects/${projectId}/videos/${videoId}/scenes?is_short=true`);
}

export async function getShortAudioStatus(projectId: string, videoId: string): Promise<boolean> {
  try {
    const data = await request<{ exists: boolean }>(`/projects/${projectId}/videos/${videoId}/short/audio/status`);
    return data.exists;
  } catch { return false; }
}

export async function bulkCreateShortScenes(projectId: string, videoId: string, scenes: SceneBulkItem[]): Promise<Scene[]> {
  return request<Scene[]>(`/projects/${projectId}/videos/${videoId}/scenes/bulk?is_short=true`, {
    method: 'POST',
    body: JSON.stringify({ scenes }),
  });
}

export async function deleteAllShortScenes(projectId: string, videoId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/projects/${projectId}/videos/${videoId}/scenes?is_short=true`, { method: 'DELETE' });
}

export async function streamGenerateAllShortPrompts(
  projectId: string,
  videoId: string,
  onEvent: (event: BatchPromptEvent) => void | Promise<void>,
  mode: 'all' | 'missing' = 'missing',
  signal?: AbortSignal,
): Promise<void> {
  const url = `${CHAT_URL}/api/generate-all-prompts/${projectId}/${videoId}?mode=${mode}&is_short=true`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    onEvent({ type: 'error', message: `API error ${res.status}: ${errorBody}` });
    return;
  }
  const reader = res.body?.getReader();
  if (!reader) { onEvent({ type: 'error', message: 'No response stream' }); return; }
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        try {
          const evt: BatchPromptEvent = JSON.parse(jsonStr);
          await onEvent(evt);
        } catch { /* skip malformed JSON */ }
      }
    }
  } catch (e) {
    if (signal?.aborted) return;
    throw e;
  }
}

export async function streamGenerateShortAssets(
  projectId: string,
  videoId: string,
  onEvent: (event: SceneAssetEvent) => Promise<void> | void,
  mode: 'all' | 'missing' = 'missing',
  signal?: AbortSignal,
  sceneNumbers?: number[],
  visualTypeFilter?: 'image' | 'video',
): Promise<void> {
  const params = new URLSearchParams({ mode, is_short: 'true' });
  if (sceneNumbers && sceneNumbers.length > 0) params.set('scenes_filter', sceneNumbers.join(','));
  if (visualTypeFilter) params.set('visual_type_filter', visualTypeFilter);
  const resp = await fetch(`${CHAT_URL}/api/generate-scene-assets/${projectId}/${videoId}?${params}`, {
    method: 'POST',
    signal,
  });
  if (!resp.ok || !resp.body) throw new Error('SSE connection failed');
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6)) as SceneAssetEvent;
            await onEvent(event);
          } catch { /* skip malformed */ }
        }
      }
    }
  } catch (e) {
    if (signal?.aborted) return;
    throw e;
  }
}

export function getShortChatHistory(projectId: string, videoId: string): Promise<{ messages: ChatMessage[] }> {
  return chatRequest<{ messages: ChatMessage[] }>(`/api/chat/${projectId}/${videoId}/short`);
}

export async function streamShortChat(
  projectId: string, videoId: string, message: string,
  onDelta: (text: string) => void, onDone: (fullText: string) => void, onError: (error: string) => void,
): Promise<void> {
  const url = `${CHAT_URL}/api/chat/${projectId}/${videoId}/short/stream`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) { onError(`API error ${res.status}`); return; }
  const reader = res.body?.getReader();
  if (!reader) { onError('No stream'); return; }
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const evt = JSON.parse(line.slice(6).trim());
        if (evt.type === 'delta') onDelta(evt.text);
        else if (evt.type === 'done') onDone(evt.text);
        else if (evt.type === 'error') onError(evt.text);
      } catch { /* skip */ }
    }
  }
}

export async function finalizeShort(projectId: string, videoId: string): Promise<{ status: string; saved?: { type: string; tag: string }[] }> {
  return chatRequest<{ status: string; saved?: { type: string; tag: string }[] }>(`/api/chat/${projectId}/${videoId}/short/finalize`, { method: 'POST' });
}

export async function generateShortShotlist(projectId: string, videoId: string): Promise<{ status: string; scenes?: unknown[] }> {
  return chatRequest<{ status: string }>(`/api/generate-shotlist/${projectId}/${videoId}?is_short=true`, { method: 'POST' });
}

// ---- Templates ----

export interface Template {
  id: string;
  name: string;
  category: string;
  description: string;
  preview_summary: string;
  applies_to: string[];
  content: string;
}

export interface TemplatesResponse {
  image_styles: Template[];
  edit_styles: Template[];
  storytelling_profiles: Template[];
}

export async function getTemplates(): Promise<TemplatesResponse> {
  return request<TemplatesResponse>('/templates');
}

export async function applyTemplateToProject(
  category: string, templateId: string, projectId: string, targetGuide: string
): Promise<{ status: string }> {
  return request<{ status: string }>(`/templates/${category}/${templateId}/apply/${projectId}`, {
    method: 'POST',
    body: JSON.stringify({ target_guide: targetGuide }),
  });
}

export async function applyTemplateToVideo(
  category: string, templateId: string, projectId: string, videoId: string, targetGuide: string
): Promise<{ status: string }> {
  return request<{ status: string }>(`/templates/${category}/${templateId}/apply/${projectId}/${videoId}`, {
    method: 'POST',
    body: JSON.stringify({ target_guide: targetGuide }),
  });
}

// ---- Settings ----

export interface AppSettings {
  export_method: 'ffmpeg' | 'capcut';
  default_video_duration: number;
  veo3_clip_duration: number;
  bgm_volume: number;
  subtitle_burn_in: boolean;
  transition_type: 'crossfade' | 'fade_black' | 'cut';
  transition_duration: number;
}

export async function getSettings(): Promise<AppSettings> {
  return request<AppSettings>('/settings');
}

export async function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return request<AppSettings>('/settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ---- Chat (via Chat Bridge on port 8001) ----

const CHAT_URL = 'http://localhost:8001';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

async function chatRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${CHAT_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    throw new Error(`Chat API error ${res.status}: ${errorBody}`);
  }
  return res.json();
}

export async function getChatHistory(projectId: string, videoId: string): Promise<{ messages: ChatMessage[] }> {
  return chatRequest<{ messages: ChatMessage[] }>(`/api/chat/${projectId}/${videoId}`);
}

export async function sendChatMessage(projectId: string, videoId: string, message: string): Promise<ChatMessage> {
  return chatRequest<ChatMessage>(`/api/chat/${projectId}/${videoId}`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export async function streamChatMessage(
  projectId: string,
  videoId: string,
  message: string,
  onDelta: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
): Promise<void> {
  const url = `${CHAT_URL}/api/chat/${projectId}/${videoId}/stream`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    onError(`Chat API error ${res.status}: ${errorBody}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) { onError('No response stream'); return; }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6).trim();
      if (!jsonStr) continue;
      try {
        const evt = JSON.parse(jsonStr);
        if (evt.type === 'delta') {
          onDelta(evt.text);
        } else if (evt.type === 'done') {
          onDone(evt.text);
        } else if (evt.type === 'error') {
          onError(evt.text);
        }
      } catch { /* skip malformed JSON */ }
    }
  }
}

export async function clearChatHistory(projectId: string, videoId: string): Promise<{ status: string }> {
  return chatRequest<{ status: string }>(`/api/chat/${projectId}/${videoId}`, {
    method: 'DELETE',
  });
}

export async function finalizeChatScript(projectId: string, videoId: string, kbCode?: string, ndCode?: string): Promise<{ status: string; saved: Record<string, string> }> {
  return chatRequest<{ status: string; saved: Record<string, string> }>(`/api/chat/${projectId}/${videoId}/finalize`, {
    method: 'POST',
    body: JSON.stringify({ kb_code: kbCode || null, nd_code: ndCode || null }),
  });
}

export interface DraftInfo {
  tag: string;
  code: string;
  label: string;
  preview: string;
  length: number;
  message_index: number;
}

export async function getChatDrafts(projectId: string, videoId: string): Promise<{ drafts: DraftInfo[] }> {
  return chatRequest<{ drafts: DraftInfo[] }>(`/api/chat/${projectId}/${videoId}/drafts`);
}

export async function checkChatHealth(): Promise<{ status: string; sdk_pool?: SdkPoolStats }> {
  return chatRequest<{ status: string; sdk_pool?: SdkPoolStats }>('/health');
}

// ---- Batch Prompt Generation (SSE) ----

export interface BatchPromptEvent {
  type: 'status' | 'plan_done' | 'scene_done' | 'all_done' | 'error' | 'stopped';
  message?: string;
  scene_number?: number;
  veo3_prompt?: string;
  visual_type?: string;
  mood?: string;
  status?: string;
  progress?: string;
  edit_plan?: EditPlan;
  plan?: Array<{ scene_number: number; visual_brief: string; visual_type: string; mood: string }>;
}

export async function streamGenerateAllPrompts(
  projectId: string,
  videoId: string,
  onEvent: (event: BatchPromptEvent) => void | Promise<void>,
  mode: 'all' | 'missing' = 'missing',
  signal?: AbortSignal,
): Promise<void> {
  const url = `${CHAT_URL}/api/generate-all-prompts/${projectId}/${videoId}?mode=${mode}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    onEvent({ type: 'error', message: `API error ${res.status}: ${errorBody}` });
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) { onEvent({ type: 'error', message: 'No response stream' }); return; }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        try {
          const evt: BatchPromptEvent = JSON.parse(jsonStr);
          await onEvent(evt);
        } catch { /* skip malformed JSON */ }
      }
    }
  } catch (e) {
    if (signal?.aborted) return;
    throw e;
  }
}

// ---- Monitor (via Chat Bridge on port 8001) ----

export interface MonitorActivity {
  id: string;
  timestamp: string;
  category: string; // chat, prompt, character, shotlist, system
  action: string;
  detail: string;
  project_id: string;
  video_id: string;
  status: string; // info, success, error, working
  job_id: string;
  type?: string; // for SSE events: connected, heartbeat
}

export interface MonitorJob {
  job_id: string;
  category: string;
  action: string;
  project_id: string;
  video_id: string;
  started_at: string;
  finished_at?: string;
  total: number;
  completed: number;
  status: string;
}

export interface SdkPoolStats {
  pool_size: number;
  total_created: number;
  available: number;
  in_use: number;
}

export interface MonitorStatus {
  server: string;
  sdk_pool: SdkPoolStats;
  active_jobs: MonitorJob[];
  cancel_flags: string[];
  total_activities: number;
}

// ---- Lab (Phòng nghiên cứu) ----

export interface LabSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export async function getLabSessions(labType: string): Promise<{ sessions: LabSession[] }> {
  return chatRequest<{ sessions: LabSession[] }>(`/api/lab/${labType}/sessions`);
}

export async function createLabSession(labType: string, title?: string): Promise<LabSession> {
  return chatRequest<LabSession>(`/api/lab/${labType}/sessions`, {
    method: 'POST',
    body: JSON.stringify({ title: title || null }),
  });
}

export async function deleteLabSession(labType: string, sessionId: string): Promise<{ status: string }> {
  return chatRequest<{ status: string }>(`/api/lab/${labType}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

export async function getLabSessionHistory(labType: string, sessionId: string): Promise<{ messages: ChatMessage[]; title: string }> {
  return chatRequest<{ messages: ChatMessage[]; title: string }>(`/api/lab/${labType}/sessions/${sessionId}/history`);
}

export async function streamLabChat(
  labType: string,
  sessionId: string,
  message: string,
  onDelta: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
): Promise<void> {
  const url = `${CHAT_URL}/api/lab/${labType}/sessions/${sessionId}/stream`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    onError(`Lab API error ${res.status}: ${errorBody}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) { onError('No response stream'); return; }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6).trim();
      if (!jsonStr) continue;
      try {
        const evt = JSON.parse(jsonStr);
        if (evt.type === 'delta') {
          onDelta(evt.text);
        } else if (evt.type === 'done') {
          onDone(evt.text);
        } else if (evt.type === 'error') {
          onError(evt.text);
        }
      } catch { /* skip malformed JSON */ }
    }
  }
}

export interface LabSaveResult {
  status: string;
  tag: string;
  template_id: string;
  name: string;
  category: string;
  path: string;
}

export async function saveLabOutput(labType: string, sessionId: string, tag: string, code?: string): Promise<LabSaveResult> {
  return chatRequest<LabSaveResult>(`/api/lab/${labType}/sessions/${sessionId}/save`, {
    method: 'POST',
    body: JSON.stringify({ tag, code: code || null }),
  });
}

export interface LabOutput {
  id: string;
  name: string;
  category: string;
  description: string;
  preview_summary: string;
}

export async function getLabOutputs(labType: string): Promise<{ outputs: LabOutput[] }> {
  return chatRequest<{ outputs: LabOutput[] }>(`/api/lab/${labType}/outputs`);
}

// ---- Monitor (via Chat Bridge on port 8001) ----

export async function getMonitorStatus(): Promise<MonitorStatus> {
  return chatRequest<MonitorStatus>('/api/monitor/status');
}

export async function getMonitorActivities(category?: string, limit?: number): Promise<MonitorActivity[]> {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (limit) params.set('limit', String(limit));
  const qs = params.toString();
  return chatRequest<MonitorActivity[]>(`/api/monitor/activities${qs ? '?' + qs : ''}`);
}

export function connectMonitorStream(
  onActivity: (activity: MonitorActivity) => void,
  onError?: (error: string) => void,
): () => void {
  const url = `${CHAT_URL}/api/monitor/stream`;
  let cancelled = false;

  async function connect() {
    while (!cancelled) {
      try {
        const res = await fetch(url);
        if (!res.ok) { onError?.(`Monitor stream error ${res.status}`); return; }
        const reader = res.body?.getReader();
        if (!reader) { onError?.('No stream'); return; }
        const decoder = new TextDecoder();
        let buffer = '';

        while (!cancelled) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const evt: MonitorActivity = JSON.parse(line.slice(6).trim());
              if (evt.type === 'heartbeat' || evt.type === 'connected') continue;
              onActivity(evt);
            } catch { /* skip */ }
          }
        }
      } catch {
        if (cancelled) return;
        // Reconnect after 3s
        await new Promise(r => setTimeout(r, 3000));
      }
    }
  }

  connect();

  return () => { cancelled = true; };
}

// ── Generation error log ──────────────────────────────────────

export interface GenerationError {
  scene_number: number;
  visual_type?: string;
  type?: string;
  error: string;
  timestamp: string;
}

export async function getGenerationErrors(projectId: string, videoId: string): Promise<GenerationError[]> {
  const res = await fetch(`${CHAT_URL}/api/generation-errors/${projectId}/${videoId}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.errors || [];
}

export async function clearGenerationErrors(projectId: string, videoId: string): Promise<void> {
  await fetch(`${CHAT_URL}/api/generation-errors/${projectId}/${videoId}`, { method: "DELETE" });
}
