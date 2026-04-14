/**
 * useSpeechInput.ts — Voice recording + transcription hook
 * Drop into: src/hooks/useSpeechInput.ts
 *
 * Records audio from the user's mic, sends to backend Whisper API,
 * returns the transcript and parsed tasks.
 */

import { useState, useRef } from "react";
import { api, type CreateTaskPayload } from "@/lib/api";

type RecordingState = "idle" | "recording" | "processing" | "done" | "error";

interface UseSpeechInputReturn {
  state: RecordingState;
  transcript: string;
  parsedTasks: CreateTaskPayload[];
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  reset: () => void;
}

export function useSpeechInput(): UseSpeechInputReturn {
  const [state, setState]           = useState<RecordingState>("idle");
  const [transcript, setTranscript] = useState("");
  const [parsedTasks, setParsedTasks] = useState<CreateTaskPayload[]>([]);
  const [error, setError]           = useState<string | null>(null);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks        = useRef<Blob[]>([]);

  const startRecording = async () => {
    setError(null);
    setTranscript("");
    setParsedTasks([]);
    chunks.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };

      recorder.onstop = async () => {
        setState("processing");
        stream.getTracks().forEach(t => t.stop());

        const audioBlob = new Blob(chunks.current, { type: "audio/webm" });
        try {
          const result = await api.speech.transcribe(audioBlob);
          setTranscript(result.text);
          setParsedTasks(result.parsed_tasks || []);
          setState("done");
        } catch (e: any) {
          setError(e.message || "Transcription failed");
          setState("error");
        }
      };

      mediaRecorder.current = recorder;
      recorder.start();
      setState("recording");
    } catch (e: any) {
      setError("Microphone access denied");
      setState("error");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && state === "recording") {
      mediaRecorder.current.stop();
    }
  };

  const reset = () => {
    setState("idle");
    setTranscript("");
    setParsedTasks([]);
    setError(null);
  };

  return { state, transcript, parsedTasks, error, startRecording, stopRecording, reset };
}
