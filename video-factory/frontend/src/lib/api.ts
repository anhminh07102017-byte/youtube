const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  created_at?: string;
  updated_at?: string;
}

export interface Script {
  content: string;
  status: string;
  updated_at?: string;
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

// ---- Scenes ----

export async function getScenes(projectId: string, videoId: string): Promise<Scene[]> {
  return request<Scene[]>(`/projects/${projectId}/videos/${videoId}/scenes`);
}

export async function updateScene(
  projectId: string,
  videoId: string,
  sceneNumber: number,
  data: Partial<Scene>
): Promise<Scene> {
  return request<Scene>(`/projects/${projectId}/videos/${videoId}/scenes/${sceneNumber}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function updateSceneStatus(
  projectId: string,
  videoId: string,
  sceneNumber: number,
  status: string
): Promise<Scene> {
  return request<Scene>(`/projects/${projectId}/videos/${videoId}/scenes/${sceneNumber}/status`, {
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

export async function getCharacters(projectId: string): Promise<Character[]> {
  return request<Character[]>(`/projects/${projectId}/characters`);
}

export async function createCharacter(projectId: string, data: Omit<Character, 'id'>): Promise<Character> {
  return request<Character>(`/projects/${projectId}/characters`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getCharacter(projectId: string, characterId: string): Promise<Character> {
  return request<Character>(`/projects/${projectId}/characters/${characterId}`);
}

export async function updateCharacter(projectId: string, characterId: string, data: Partial<Character>): Promise<Character> {
  return request<Character>(`/projects/${projectId}/characters/${characterId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteCharacter(projectId: string, characterId: string): Promise<void> {
  await request<void>(`/projects/${projectId}/characters/${characterId}`, {
    method: 'DELETE',
  });
}

export async function extractCharacters(projectId: string, videoId: string): Promise<{ status: string; characters?: Omit<Character, 'id' | 'project_id'>[]; message?: string }> {
  return chatRequest<{ status: string; characters?: Omit<Character, 'id' | 'project_id'>[]; message?: string }>(`/api/extract-characters/${projectId}/${videoId}`, {
    method: 'POST',
  });
}

export async function flowLogin(): Promise<{ status: string; logged_in: boolean; message: string }> {
  return chatRequest<{ status: string; logged_in: boolean; message: string }>('/api/flow-login', { method: 'POST' });
}

export async function flowStatus(): Promise<{ logged_in: boolean }> {
  return chatRequest<{ logged_in: boolean }>('/api/flow-status');
}

export async function generateCharacterImage(projectId: string, characterId: string): Promise<{ status: string; image_path?: string; flow_character_id?: string; error?: string }> {
  return chatRequest<{ status: string; image_path?: string; flow_character_id?: string; error?: string }>(`/api/generate-character-image/${projectId}/${characterId}`, {
    method: 'POST',
  });
}

export async function generateAllCharacterImages(projectId: string): Promise<{ status: string; results: { id: string; name: string; status: string; image_path?: string; error?: string }[] }> {
  return chatRequest<{ status: string; results: { id: string; name: string; status: string; image_path?: string; error?: string }[] }>(`/api/generate-all-character-images/${projectId}`, {
    method: 'POST',
  });
}

// ---- Export ----

export async function buildCapcutProject(projectId: string, videoId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/projects/${projectId}/videos/${videoId}/export/capcut`, {
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

export async function updateVideoGuide(projectId: string, videoId: string, guideName: string, content: string): Promise<{ content: string; updated_at: string }> {
  return request<{ content: string; updated_at: string }>(`/projects/${projectId}/videos/${videoId}/guides/${guideName}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
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

export async function checkChatHealth(): Promise<{ status: string; claude_available: boolean }> {
  return chatRequest<{ status: string; claude_available: boolean }>('/health');
}

// ---- Batch Prompt Generation (SSE) ----

export interface BatchPromptEvent {
  type: 'status' | 'plan_done' | 'scene_done' | 'all_done' | 'error';
  message?: string;
  scene_number?: number;
  veo3_prompt?: string;
  visual_type?: string;
  mood?: string;
  status?: string;
  progress?: string;
  plan?: Array<{ scene_number: number; visual_brief: string; visual_type: string; mood: string }>;
}

export async function streamGenerateAllPrompts(
  projectId: string,
  videoId: string,
  onEvent: (event: BatchPromptEvent) => void,
  mode: 'all' | 'missing' = 'missing',
): Promise<void> {
  const url = `${CHAT_URL}/api/generate-all-prompts/${projectId}/${videoId}?mode=${mode}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
        onEvent(evt);
      } catch { /* skip malformed JSON */ }
    }
  }
}
