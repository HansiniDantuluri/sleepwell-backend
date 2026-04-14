/**
 * useFocusTimer.ts — Focus mode timer hook with backend XP tracking
 * Drop into: src/hooks/useFocusTimer.ts
 */

import { useState, useEffect, useRef } from "react";
import { api, type FocusSession } from "@/lib/api";

interface UseFocusTimerReturn {
  secondsLeft: number;
  isRunning: boolean;
  isComplete: boolean;
  xpEarned: number;
  currentSession: FocusSession | null;
  start: (taskTitle: string, durationMinutes?: number, taskId?: number) => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: (completed?: boolean) => Promise<void>;
  progress: number; // 0-1
}

export function useFocusTimer(): UseFocusTimerReturn {
  const [secondsLeft, setSecondsLeft] = useState(25 * 60);
  const [totalSeconds, setTotalSeconds] = useState(25 * 60);
  const [isRunning, setIsRunning]     = useState(false);
  const [isComplete, setIsComplete]   = useState(false);
  const [xpEarned, setXpEarned]       = useState(0);
  const [currentSession, setCurrentSession] = useState<FocusSession | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Tick down every second when running
  useEffect(() => {
    if (isRunning) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft(prev => {
          if (prev <= 1) {
            clearInterval(intervalRef.current!);
            setIsRunning(false);
            setIsComplete(true);
            // Auto-end the session when timer hits 0
            if (currentSession) {
              api.focus.end(currentSession.id, true).then(s => setXpEarned(s.xp_earned));
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(intervalRef.current!);
  }, [isRunning, currentSession]);

  const start = async (taskTitle: string, durationMinutes = 25, taskId?: number) => {
    const session = await api.focus.start({ task_title: taskTitle, duration_minutes: durationMinutes, task_id: taskId });
    setCurrentSession(session);
    const secs = durationMinutes * 60;
    setSecondsLeft(secs);
    setTotalSeconds(secs);
    setIsComplete(false);
    setXpEarned(0);
    setIsRunning(true);
  };

  const pause  = () => setIsRunning(false);
  const resume = () => setIsRunning(true);

  const stop = async (completed = false) => {
    setIsRunning(false);
    if (currentSession) {
      const ended = await api.focus.end(currentSession.id, completed);
      setXpEarned(ended.xp_earned);
    }
    setIsComplete(true);
  };

  return {
    secondsLeft,
    isRunning,
    isComplete,
    xpEarned,
    currentSession,
    start,
    pause,
    resume,
    stop,
    progress: totalSeconds > 0 ? 1 - secondsLeft / totalSeconds : 0,
  };
}
