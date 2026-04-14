/**
 * useSchedule.ts — AI Schedule generation hook
 * Drop into: src/hooks/useSchedule.ts
 *
 * This drives the "Plan My Day" screen.
 */

import { useState } from "react";
import { api, type Schedule, type Task } from "@/lib/api";

interface UseScheduleReturn {
  schedule: Schedule | null;
  loading: boolean;
  error: string | null;
  warnings: string[];
  generate: (opts: GenerateOptions) => Promise<Schedule | null>;
  loadForDate: (date: string) => Promise<void>;
  clear: () => void;
}

interface GenerateOptions {
  date: string;
  taskIds?: number[];
  freeText?: string;       // typed or speech-to-text input
}

export function useSchedule(): UseScheduleReturn {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  const generate = async ({ date, taskIds, freeText }: GenerateOptions) => {
    setLoading(true);
    setError(null);
    setWarnings([]);
    try {
      const result = await api.schedule.generate({
        date,
        task_ids: taskIds,
        free_text_tasks: freeText,
      });
      setSchedule(result);

      // Extract any overflow/warning info from ai_notes
      // The backend embeds this in ai_notes; you can also parse a warnings field if added
      return result;
    } catch (e: any) {
      setError(e.message || "Failed to generate schedule");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const loadForDate = async (date: string) => {
    setLoading(true);
    try {
      const result = await api.schedule.getByDate(date);
      setSchedule(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const clear = () => {
    setSchedule(null);
    setError(null);
    setWarnings([]);
  };

  return { schedule, loading, error, warnings, generate, loadForDate, clear };
}
