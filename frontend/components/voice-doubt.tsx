"use client";

import { useEffect, useRef, useState } from "react";

import { submitVoiceDoubt, type VoiceDoubtResult } from "../lib/api";

type VoiceDoubtProps = { studentId: string; subjectId: string; activeContext: string; onReply: (result: VoiceDoubtResult) => void };

export function VoiceDoubt({ studentId, subjectId, activeContext, onReply }: VoiceDoubtProps) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "recording" | "sending" | "error">("idle");
  const [message, setMessage] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stopTimer = useRef<number | null>(null);

  useEffect(() => () => {
    if (stopTimer.current) window.clearTimeout(stopTimer.current);
    recorder.current?.stream.getTracks().forEach((track) => track.stop());
  }, []);

  async function startRecording() {
    setMessage("");
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setStatus("error"); setMessage("Voice recording is not available in this browser."); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = preferredMimeType();
      const nextRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunks.current = []; recorder.current = nextRecorder;
      nextRecorder.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      nextRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        if (stopTimer.current) window.clearTimeout(stopTimer.current);
        if (chunks.current.length) void sendRecording(new Blob(chunks.current, { type: nextRecorder.mimeType || "audio/webm" }));
      };
      nextRecorder.start(); setStatus("recording"); stopTimer.current = window.setTimeout(stopRecording, 30_000);
    } catch { setStatus("error"); setMessage("Please allow microphone access, then try again."); }
  }

  function stopRecording() { if (recorder.current?.state === "recording") recorder.current.stop(); }
  function cancelRecording() {
    chunks.current = [];
    if (recorder.current?.state === "recording") recorder.current.onstop = () => recorder.current?.stream.getTracks().forEach((track) => track.stop());
    stopRecording(); setStatus("idle");
  }
  async function sendRecording(audio: Blob) {
    setStatus("sending");
    try { const result = await submitVoiceDoubt(studentId, subjectId, audio, activeContext); onReply(result); setStatus("idle"); setOpen(false); }
    catch (cause) { setStatus("error"); setMessage(cause instanceof Error ? cause.message : "We could not hear that recording. Please try again."); }
  }

  return <div className="fixed bottom-5 right-5 z-30 sm:bottom-7 sm:right-7">
    {open && <section className="animate-card-enter absolute bottom-16 right-0 w-[min(18rem,calc(100vw-2.5rem))] rounded-[1.5rem] border border-white/10 bg-[var(--bg-primary)] p-5 text-[var(--text-inverse)] shadow-2xl" aria-live="polite">
      <p className="tutor-display text-2xl font-semibold">Talk it through</p>
      <p className="mt-1 text-sm leading-5 text-[#d3dcde]">Record up to 30 seconds. It is used only to respond to this doubt.</p>
      {status === "recording" && <p className="mt-4 flex items-center gap-2 text-sm font-medium"><span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[var(--accent-mastery)]" />Listening…</p>}
      {message && <p className="mt-3 text-sm text-[#f1c5bd]">{message}</p>}
      <div className="mt-5 flex gap-2">
        {status === "recording" ? <><button onClick={stopRecording} className="rounded-full bg-[var(--accent-mastery)] px-4 py-2 text-sm font-medium text-white">Stop & send</button><button onClick={cancelRecording} className="rounded-full border border-white/25 px-4 py-2 text-sm">Cancel</button></> : <button disabled={status === "sending"} onClick={startRecording} className="rounded-full bg-[var(--accent-mastery)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{status === "sending" ? "Thinking…" : "Start recording"}</button>}
      </div>
    </section>}
    <button aria-label="Ask the Educator a question by voice" aria-expanded={open} onClick={() => setOpen((value) => !value)} className="animate-doubt-pulse grid h-14 w-14 place-items-center rounded-full border-4 border-[var(--surface)] bg-[var(--accent-mastery)] text-2xl font-semibold text-white shadow-lg transition-transform active:scale-90">!</button>
  </div>;
}

function preferredMimeType() { return ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type)) ?? ""; }
