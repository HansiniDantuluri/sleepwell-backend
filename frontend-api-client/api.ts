/**
 * api.ts — SleepWell frontend API client
 * 
 * Drop this file into your React project at: src/lib/api.ts
 * It provides typed functions for every backend endpoint.
 * 
 * Usage:
 *   import { api } from "@/lib/api";
 *   const schedule = await api.schedule.generate({ date: "2024-10-15", free_text_tasks: "gym 1hr, report by 5pm" });
 */

const BASE_URL = "http://localhost:8000/api";

// ─── Auth token storage ──────────────────────────────────────────────────────

export const tokenStore = {
  get: () => localStorage.getItem("sleepwell_token"),
  set: (token: string) => localStorage.setItem("sleepwell_token", token),
  clear: () => localStorage.removeItem("sleepwell_token"),
};

// ─── Base fetch with auth ────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = tokenStore.get();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }

  if (res.status === 204) return null as T;
  return res.json();
}

// ─── API client ──────────────────────────────────────────────────────────────

export const api = {
  // Auth
  auth: {
    register: (email: string, password: string, name?: string) =>
      apiFetch<{ access_token: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, name }),
      }),

    login: (email: string, password: string) =>
      apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
  },

  // User profile & onboarding
  users: {
    me: () => apiFetch<UserProfile>("/users/me"),

    saveOnboarding: (data: OnboardingPayload) =>
      apiFetch<UserProfile>("/users/onboarding", {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    updateProfile: (data: Partial<OnboardingPayload>) =>
      apiFetch<UserProfile>("/users/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },

  // Tasks
  tasks: {
    list: (date_for?: string) =>
      apiFetch<Task[]>(`/tasks${date_for ? `?date_for=${date_for}` : ""}`),

    create: (task: CreateTaskPayload) =>
      apiFetch<Task>("/tasks", { method: "POST", body: JSON.stringify(task) }),

    update: (id: number, updates: Partial<CreateTaskPayload>) =>
      apiFetch<Task>(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(updates) }),

    delete: (id: number) =>
      apiFetch<null>(`/tasks/${id}`, { method: "DELETE" }),

    complete: (id: number) =>
      apiFetch<Task>(`/tasks/${id}/complete`, { method: "PATCH" }),
  },

  // AI Schedule
  schedule: {
    generate: (payload: ScheduleRequest) =>
      apiFetch<Schedule>("/schedule/generate", {
        method: "POST",
        body: JSON.stringify(payload),
      }),

    getByDate: (date: string) =>
      apiFetch<Schedule | null>(`/schedule/${date}`),

    list: () => apiFetch<Schedule[]>("/schedule/"),
  },

  // Focus sessions
  focus: {
    start: (payload: { task_id?: number; task_title?: string; duration_minutes: number }) =>
      apiFetch<FocusSession>("/focus/start", {
        method: "POST",
        body: JSON.stringify(payload),
      }),

    end: (sessionId: number, completed: boolean = true) =>
      apiFetch<FocusSession>(`/focus/${sessionId}/end`, {
        method: "POST",
        body: JSON.stringify({ completed }),
      }),

    history: () => apiFetch<FocusSession[]>("/focus/"),
  },

  // Progress
  progress: {
    stats: () => apiFetch<ProgressStats>("/progress/stats"),

    logSleep: (payload: SleepLogPayload) =>
      apiFetch<SleepLog>("/progress/sleep-log", {
        method: "POST",
        body: JSON.stringify(payload),
      }),

    sleepLogs: (days: number = 7) =>
      apiFetch<SleepLog[]>(`/progress/sleep-logs?days=${days}`),
  },

  // Speech to text
  speech: {
    transcribe: async (audioBlob: Blob): Promise<TranscriptionResult> => {
      const token = tokenStore.get();
      const form = new FormData();
      form.append("audio", audioBlob, "recording.webm");
      const res = await fetch(`${BASE_URL}/speech/transcribe`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      if (!res.ok) throw new Error("Transcription failed");
      return res.json();
    },

    parseText: (text: string) =>
      apiFetch<TranscriptionResult>("/speech/parse-text", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
  },
};

// ─── Types (mirror backend schemas) ─────────────────────────────────────────

export interface UserProfile {
  id: number;
  email: string;
  name?: string;
  sleep_goal_hours: number;
  bedtime_target: string;
  wake_time_target: string;
  stress_level: string;
}

export interface OnboardingPayload {
  sleep_goal_hours: number;
  bedtime_target: string;
  wake_time_target: string;
  stress_level: string;
  onboarding_data?: unknown;
}

export interface Task {
  id: number;
  title: string;
  task_type: string;
  priority: string;
  estimated_minutes: number;
  deadline?: string;
  notes?: string;
  is_completed: boolean;
  date_for?: string;
  created_at: string;
}

export interface CreateTaskPayload {
  title: string;
  task_type?: string;
  priority?: string;
  estimated_minutes?: number;
  deadline?: string;
  notes?: string;
  date_for?: string;
}

export interface ScheduleRequest {
  date: string;
  task_ids?: number[];
  free_text_tasks?: string;
}

export interface ScheduleBlock {
  id: number;
  task_id?: number;
  block_type: string;
  title: string;
  start_time: string;
  end_time: string;
  is_locked: boolean;
  is_auto_adjusted: boolean;
  color: string;
}

export interface Schedule {
  id: number;
  date: string;
  ai_notes?: string;
  confidence: number;
  blocks: ScheduleBlock[];
}

export interface FocusSession {
  id: number;
  task_title?: string;
  duration_minutes: number;
  completed: boolean;
  xp_earned: number;
  started_at: string;
  ended_at?: string;
}

export interface SleepLog {
  id: number;
  date: string;
  bedtime_actual?: string;
  wake_time_actual?: string;
  sleep_hours?: number;
  quality_score?: number;
  schedule_adherence?: number;
}

export interface SleepLogPayload {
  date: string;
  bedtime_actual?: string;
  wake_time_actual?: string;
  sleep_hours?: number;
  quality_score?: number;
  schedule_adherence?: number;
}

export interface ProgressStats {
  streak_days: number;
  avg_sleep_hours: number;
  avg_adherence: number;
  total_focus_sessions: number;
  total_xp: number;
  sleep_logs: SleepLog[];
}

export interface TranscriptionResult {
  text: string;
  parsed_tasks?: CreateTaskPayload[];
}
