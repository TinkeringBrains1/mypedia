"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { StudentDashboard } from "../components/student-dashboard";
import { LeftSidebar } from "../components/left-sidebar";
import { VoiceDoubt } from "../components/voice-doubt";
import {
  getLearningMemory, getNextDiagnosticQuestion, getPrerequisiteCheck, getSubjects, getTeachingTurn, startDiagnostic,
  pauseSession, submitCheckResponse, submitDiagnostic, submitPrerequisiteCheck, submitStudentSignal,
  type DiagnosticQuestion, type DiagnosticResponse, type LearningMemoryApi, type PrerequisiteCheck,
  type Subject, type TeachingTurn, type VoiceDoubtResult,
} from "../lib/api";
import { clearStudentSession, readStudentSession, saveStudentSession, type StudentSession } from "../lib/student-session";

type Screen = "welcome" | "subjects" | "diagnostic" | "checkin" | "prerequisite" | "teaching" | "check" | "complete" | "dashboard";
type Checkin = "confident" | "unsure" | "anxious";

const conceptNodes = [
  { id: "negative_numbers", label: "Negative numbers" },
  { id: "distributive_property", label: "Distributive property" },
  { id: "combining_like_terms", label: "Combining like terms" },
  { id: "one_step_equations", label: "One-step equations" },
  { id: "two_step_equations", label: "Two-step equations" },
  { id: "variables_both_sides", label: "Variables on both sides" },
  { id: "fractions_in_equations", label: "Fractions in equations" },
];

export default function HomePage() {
  const [screen, setScreen] = useState<Screen>("welcome");
  const [authenticated, setAuthenticated] = useState(false);
  const [authUsername, setAuthUsername] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [name, setName] = useState("");
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [studentId, setStudentId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [diagnosticQuestions, setDiagnosticQuestions] = useState<DiagnosticQuestion[]>([]);
  const [diagnosticIndex, setDiagnosticIndex] = useState(0);
  const [diagnosticSessionId, setDiagnosticSessionId] = useState("");
  const [responses, setResponses] = useState<DiagnosticResponse[]>([]);
  const [prerequisite, setPrerequisite] = useState<{ lessonNode: string; check: PrerequisiteCheck } | null>(null);
  const [teachingTurn, setTeachingTurn] = useState<TeachingTurn | null>(null);
  const [adaptationNote, setAdaptationNote] = useState("");
  const [memory, setMemory] = useState<LearningMemoryApi | null>(null);
  const [answers, setAnswers] = useState<string[]>([]);
  const [voiceReply, setVoiceReply] = useState<VoiceDoubtResult | null>(null);
  const [resumableSession, setResumableSession] = useState<StudentSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [idlePrompt, setIdlePrompt] = useState(false);
  const [idleReset, setIdleReset] = useState(0);
  const startedAt = useRef(Date.now());

  useEffect(() => {
    getSubjects().then(setSubjects).catch((cause: Error) => setError(cause.message));
    setResumableSession(readStudentSession());
    if (window.sessionStorage.getItem("mypedia_demo_authenticated") === "true") setAuthenticated(true);
  }, []);
  useEffect(() => {
    if (!authenticated || !resumableSession || new URLSearchParams(window.location.search).get("continue") !== "1") return;
    window.history.replaceState({}, "", window.location.pathname);
    void resumeLearning();
  }, [authenticated, resumableSession]);
  useEffect(() => {
    if (!voiceReply || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(voiceReply.reply_text));
    return () => window.speechSynthesis.cancel();
  }, [voiceReply]);

  const activeContext = useMemo(() => {
    if (screen === "diagnostic") return diagnosticQuestions[diagnosticIndex]?.prompt ?? "A diagnostic question.";
    if (screen === "prerequisite") return prerequisite ? `${prerequisite.check.multiple_choice.prompt}\n${prerequisite.check.text_prompt}` : "A prerequisite check.";
    if (screen === "teaching") return teachingTurn?.teaching_content ?? "A lesson.";
    if (screen === "check") return teachingTurn?.check_questions.join("\n") ?? "A learning check.";
    return "A Maths learning activity.";
  }, [diagnosticIndex, diagnosticQuestions, prerequisite, screen, teachingTurn]);

  useEffect(() => {
    setVoiceReply(null);
  }, [activeContext]);

  useEffect(() => {
    if (!studentId || !subjectId || !["teaching", "check"].includes(screen)) return;
    const timer = window.setTimeout(() => setIdlePrompt(true), 7 * 60_000);
    return () => window.clearTimeout(timer);
  }, [screen, teachingTurn, studentId, subjectId, idleReset]);

  function begin(event: FormEvent) {
    event.preventDefault();
    const studentName = name.trim();
    if (!studentName) return;
    setStudentId(`stu_${crypto.randomUUID()}`);
    setName(studentName);
    setError("");
    setScreen("subjects");
  }

  function authenticate(event: FormEvent) {
    event.preventDefault();
    if (authUsername === "user123" && authPassword === "devpost12345") {
      window.sessionStorage.setItem("mypedia_demo_authenticated", "true");
      setAuthenticated(true); setAuthError(""); return;
    }
    setAuthError("Those credentials don’t match. Please try again.");
  }

  async function selectSubject(subject: Subject) {
    setBusy(true); setError("");
    try {
      const diagnostic = await startDiagnostic(subject.id);
      setSubjectId(subject.id); setDiagnosticSessionId(diagnostic.diagnostic_session_id); setDiagnosticQuestions([diagnostic.question]); setDiagnosticIndex(0); setResponses([]); startedAt.current = Date.now(); setScreen("diagnostic");
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function answerDiagnostic(optionId: string) {
    const question = diagnosticQuestions[diagnosticIndex];
    if (!question) return;
    setBusy(true); setError("");
    const updated = [...responses, { question_id: question.id, selected_option_id: optionId, response_latency_sec: elapsedSeconds(startedAt.current), used_hint: false, attempt_count: 1 }];
    try {
      setResponses(updated);
      if (diagnosticQuestions.length === 1) {
        const next = await getNextDiagnosticQuestion(subjectId, diagnosticSessionId, updated[0]);
        setDiagnosticQuestions([question, next.question]); setDiagnosticIndex(1); startedAt.current = Date.now();
      } else setScreen("checkin");
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function finishDiagnostic(checkin: Checkin) {
    setBusy(true); setError("");
    try {
      const result = await submitDiagnostic(studentId, diagnosticSessionId, responses, checkin);
      setMemory(result.learning_memory);
      saveStudentSession({ studentId, studentName: name, subjectId });
      await beginLesson();
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function beginLesson() {
    const preflight = await getPrerequisiteCheck(studentId, subjectId);
    setVoiceReply(null);
    if (preflight.required && preflight.check) {
      setPrerequisite({ lessonNode: preflight.lesson_node, check: preflight.check }); setScreen("prerequisite"); return;
    }
    await loadTeachingTurn();
  }

  async function resumeLearning() {
    if (!resumableSession) return;
    setBusy(true); setError("");
    try {
      const resumed = await getLearningMemory(resumableSession.studentId, resumableSession.subjectId);
      setStudentId(resumableSession.studentId); setName(resumableSession.studentName); setSubjectId(resumableSession.subjectId); setMemory(resumed);
      const preflight = await getPrerequisiteCheck(resumableSession.studentId, resumableSession.subjectId);
      if (preflight.required && preflight.check) { setPrerequisite({ lessonNode: preflight.lesson_node, check: preflight.check }); setScreen("prerequisite"); }
      else {
        const turn = await getTeachingTurn(resumableSession.studentId, resumableSession.subjectId);
        setTeachingTurn(turn.teaching_turn); setAdaptationNote(noteForInstruction(turn.instruction.rule_id)); setAnswers(Array(turn.teaching_turn.check_questions.length).fill("")); setScreen("teaching");
      }
    } catch (cause) {
      const message = messageFor(cause);
      if (message.includes("No Learning Memory exists")) {
        clearStudentSession();
        setResumableSession(null);
        setScreen("welcome");
        setError("That saved demo session is no longer available. Please start a new learning path.");
      } else setError(message);
    } finally { setBusy(false); }
  }

  async function submitPrerequisite(multipleChoiceAnswer: string, textAnswer: string) {
    if (!prerequisite) return;
    setBusy(true); setError("");
    try {
      const result = await submitPrerequisiteCheck(studentId, subjectId, prerequisite.lessonNode, prerequisite.check, multipleChoiceAnswer, textAnswer);
      setMemory(result.learning_memory); setPrerequisite(null); await loadTeachingTurn();
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function loadTeachingTurn() {
    const response = await getTeachingTurn(studentId, subjectId);
    setTeachingTurn(response.teaching_turn); setAdaptationNote(noteForInstruction(response.instruction.rule_id)); setAnswers(Array(response.teaching_turn.check_questions.length).fill("")); startedAt.current = Date.now(); setScreen("teaching");
  }

  async function submitChecks() {
    if (!teachingTurn || answers.some((answer) => !answer.trim())) return;
    setBusy(true); setError(""); setIdlePrompt(false); setIdleReset((value) => value + 1);
    try {
      const result = await submitCheckResponse(studentId, subjectId, teachingTurn, answers.map((answer) => ({ answer: answer.trim(), response_latency_sec: elapsedSeconds(startedAt.current), used_hint: false, attempt_count: 1 })));
      setMemory(result.learning_memory);
      if (result.lesson_complete) setScreen("complete"); else await beginLesson();
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function sendStudentSignal(kind: "inactivity" | "struggling" | "challenge") {
    if (!studentId || !subjectId) return;
    setIdlePrompt(false);
    try { setMemory(await submitStudentSignal(studentId, subjectId, kind)); }
    catch (cause) { setError(messageFor(cause)); }
  }

  async function pauseForNow() {
    if (!studentId || !subjectId) return;
    setBusy(true); setError(""); setIdlePrompt(false);
    try {
      const updated = await pauseSession(studentId, subjectId);
      setMemory(updated); saveStudentSession({ studentId, studentName: name, subjectId }); setScreen("dashboard");
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function pauseAndOpenParent() {
    if (!studentId || !subjectId) return;
    setBusy(true); setError("");
    try {
      await pauseSession(studentId, subjectId);
      saveStudentSession({ studentId, studentName: name, subjectId });
      window.location.href = "/parent";
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function anotherExample() {
    if (!studentId || !subjectId || !teachingTurn) return;
    setBusy(true); setError(""); setIdlePrompt(false);
    try {
      const updated = await submitStudentSignal(studentId, subjectId, "struggling");
      const turn = await getTeachingTurn(studentId, subjectId, teachingTurn.teaching_content);
      setMemory(updated); setTeachingTurn(turn.teaching_turn); setAdaptationNote(noteForInstruction(turn.instruction.rule_id));
      setAnswers(Array(turn.teaching_turn.check_questions.length).fill("")); setVoiceReply(null); setIdleReset((value) => value + 1); setScreen("teaching");
    } catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  async function continuePausedSession() {
    if (!studentId || !subjectId) return;
    setBusy(true); setError("");
    try { await loadTeachingTurn(); }
    catch (cause) { setError(messageFor(cause)); } finally { setBusy(false); }
  }

  if (!authenticated) return <AuthScreen username={authUsername} password={authPassword} error={authError} setUsername={setAuthUsername} setPassword={setAuthPassword} onSubmit={authenticate} />;

  if (screen === "complete" && memory) {
    return <StudentDashboard memory={{ subjectId: memory.subject_id, sessions: memory.session_meta?.paused_sessions ?? [] }} onResume={continuePausedSession} />;
  }

  if (screen === "dashboard" && memory) return <StudentDashboard memory={{ subjectId: memory.subject_id, sessions: memory.session_meta?.paused_sessions ?? [] }} onResume={continuePausedSession} />;

  if (screen === "welcome") return <Welcome name={name} setName={setName} onSubmit={begin} resumableSession={resumableSession} onResume={resumeLearning} busy={busy} />;

  return <LearningShell name={name} subject={subjects.find((item) => item.id === subjectId)?.label} memory={memory} onSessions={pauseForNow} onParent={pauseAndOpenParent}>
    {error && <p className="mx-auto mb-4 max-w-2xl rounded-2xl border border-[var(--accent-attention)]/30 bg-[#ead8d2] px-4 py-3 text-sm" role="alert">{error}</p>}
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-5 pb-28">
      <div key={`${screen}-${diagnosticIndex}-${prerequisite?.lessonNode ?? ""}-${teachingTurn?.teaching_content ?? ""}`} className="animate-screen-enter">
        {screen === "subjects" && <Subjects subjects={subjects} busy={busy} onSelect={selectSubject} />}
        {screen === "diagnostic" && diagnosticQuestions[diagnosticIndex] && <Diagnostic question={diagnosticQuestions[diagnosticIndex]} number={diagnosticIndex + 1} busy={busy} onSelect={answerDiagnostic} />}
        {screen === "checkin" && <Checkin busy={busy} onSelect={finishDiagnostic} />}
        {screen === "prerequisite" && prerequisite && <Prerequisite check={prerequisite.check} busy={busy} onSubmit={submitPrerequisite} />}
        {screen === "teaching" && teachingTurn && <Teaching turn={teachingTurn} note={adaptationNote} pulse={memory?.session_meta?.lesson_pulse} busy={busy} onCheck={() => setScreen("check")} onSignal={sendStudentSignal} />}
        {screen === "check" && teachingTurn && <Checks answers={answers} setAnswers={setAnswers} turn={teachingTurn} busy={busy} onSubmit={submitChecks} />}
      </div>
      {voiceReply && <VoiceReply result={voiceReply} />}
      {idlePrompt && <EducatorMessage><p className="leading-6">Want to pause, or would another small example help?</p><div className="mt-4 flex gap-2"><button onClick={pauseForNow} className="rounded-full border border-[var(--border)] px-3 py-2 text-sm">Pause for now</button><button onClick={anotherExample} className="rounded-full border border-[var(--border)] px-3 py-2 text-sm">Another example</button></div></EducatorMessage>}
      {busy && <EducatorMessage><div className="flex items-center gap-2 text-sm text-[var(--muted)]"><span className="h-2 w-2 animate-pulse rounded-full bg-[var(--accent-growth)]" />Preparing the next step…</div></EducatorMessage>}
    </div>
    {studentId && subjectId && screen !== "subjects" && <VoiceDoubt studentId={studentId} subjectId={subjectId} activeContext={activeContext} onReply={(result) => { setVoiceReply(result); setMemory(result.learning_memory); }} />}
  </LearningShell>;
}

function AuthScreen({ username, password, error, setUsername, setPassword, onSubmit }: { username: string; password: string; error: string; setUsername: (value: string) => void; setPassword: (value: string) => void; onSubmit: (event: FormEvent) => void }) {
  return <main className="grid min-h-screen bg-[var(--bg-primary)] p-4 text-[var(--text-inverse)] sm:p-7"><section className="m-auto grid w-full max-w-4xl overflow-hidden rounded-[2rem] border border-white/10 lg:grid-cols-[1.1fr_.9fr]"><div className="p-8 sm:p-14"><p className="text-xs font-semibold uppercase tracking-[.16em] text-[#c9d9d0]">Mypedia · demo access</p><h1 className="tutor-display mt-7 text-5xl font-semibold leading-[.94] sm:text-6xl">Enter your learning space.</h1><p className="mt-7 max-w-md text-lg leading-7 text-[#d9dedb]">A calm, adaptive learning experience that meets each student where they are.</p></div><form onSubmit={onSubmit} className="flex flex-col justify-center bg-[var(--surface)] p-8 text-[var(--text-primary)] sm:p-12"><p className="text-xs font-semibold uppercase tracking-[.14em] text-[var(--muted)]">Sign in</p><label className="mt-7 text-sm font-medium">Username<input autoFocus value={username} onChange={(event) => setUsername(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--border)] bg-white px-4 py-3 outline-none focus:border-[var(--accent-mastery)]" autoComplete="username" /></label><label className="mt-5 text-sm font-medium">Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--border)] bg-white px-4 py-3 outline-none focus:border-[var(--accent-mastery)]" autoComplete="current-password" /></label>{error && <p className="mt-4 text-sm text-[var(--accent-attention)]" role="alert">{error}</p>}<button className="mt-6 rounded-full bg-[var(--bg-primary)] px-5 py-3 text-[var(--text-inverse)] transition hover:bg-[#273d51]">Continue <span className="float-right">→</span></button></form></section></main>;
}

function Welcome({ name, setName, onSubmit, resumableSession, onResume, busy }: { name: string; setName: (value: string) => void; onSubmit: (event: FormEvent) => void; resumableSession: StudentSession | null; onResume: () => void; busy: boolean }) {
  return <main className="grid min-h-screen bg-[var(--bg-primary)] p-4 text-[var(--text-inverse)] sm:p-7">
    <section className="m-auto grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-white/10 lg:grid-cols-[1.1fr_.9fr]">
      <div className="p-8 sm:p-14"><p className="text-xs font-semibold uppercase tracking-[.16em] text-[#c9d9d0]">Mypedia · your study space</p><h1 className="tutor-display mt-7 max-w-xl text-5xl font-semibold leading-[.94] sm:text-7xl">A calm place to learn out loud.</h1><p className="mt-7 max-w-lg text-lg leading-7 text-[#d9dedb]">Start with a few questions. Your educator shapes the next lesson around what you know and how you are feeling.</p></div>
      <form onSubmit={onSubmit} className="flex flex-col justify-end bg-[var(--surface)] p-8 text-[var(--text-primary)] sm:p-12"><p className="text-xs font-semibold uppercase tracking-[.14em] text-[var(--muted)]">Begin a conversation</p>{resumableSession && <button type="button" disabled={busy} onClick={onResume} className="mt-5 rounded-xl border border-[var(--accent-growth)] bg-[#e4ece6] px-4 py-3 text-left text-sm disabled:opacity-50">Continue {resumableSession.studentName}’s session <span className="float-right">→</span></button>}<label className="mt-7 text-lg">What should your educator call you?<input autoFocus value={name} onChange={(event) => setName(event.target.value)} maxLength={80} className="mt-3 w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3 outline-none transition focus:border-[var(--accent-mastery)] focus:ring-2 focus:ring-[#c77d3c]/20" placeholder="Your name" /></label><button className="mt-6 rounded-full bg-[var(--bg-primary)] px-6 py-3.5 text-left text-[var(--text-inverse)] transition hover:bg-[#273d51] active:scale-[.98]">Start learning <span className="float-right">→</span></button><p className="mt-5 text-sm leading-5 text-[var(--muted)]">No account needed for this MVP. Your path starts here.</p></form>
    </section>
  </main>;
}

function LearningShell({ name: _name, subject, memory, children, onSessions, onParent }: { name: string; subject?: string; memory: LearningMemoryApi | null; children: ReactNode; onSessions: () => void; onParent: () => void }) {
  return <main className={`min-h-screen bg-[var(--bg-primary)] lg:pl-[60px] ${subject ? "xl:pr-[285px]" : ""}`}>
    <section className="min-h-screen bg-[var(--surface)]"><header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--surface)]/95 px-5 py-4 backdrop-blur sm:px-8"><div><p className="tutor-display text-2xl font-semibold lg:hidden">Mypedia</p><p className="text-xs font-semibold uppercase tracking-[.14em] text-[var(--muted)]">{subject ?? "Start a learning path"}</p></div></header><div className="chat-scrollbar h-[calc(100vh-65px)] overflow-y-auto px-5 py-7 sm:px-9">{children}</div></section>
    <LeftSidebar active="learn" onLearn={() => undefined} onSessions={onSessions} onParent={onParent} />
    {subject && <ProfilePanel memory={memory} />}
  </main>;
}

function ProfilePanel({ memory }: { memory: LearningMemoryApi | null }) {
  const graph = memory?.knowledge_profile.concept_graph_position;
  return <aside className="fixed inset-y-0 right-0 z-20 hidden w-[285px] border-l border-[var(--border)] bg-[#eee7da] px-7 py-7 xl:block"><p className="text-[11px] font-semibold uppercase tracking-[.14em] text-[var(--muted)]">Your learning map</p><h2 className="tutor-display mt-2 text-3xl font-semibold">Maths</h2><p className="mt-2 text-sm leading-6 text-[var(--muted)]">A simple view of the ideas you are working through.</p><ol className="mt-10 space-y-0">{conceptNodes.map((node, index) => { const mastered = graph?.mastered_nodes.includes(node.id); const struggling = graph?.struggling_nodes.includes(node.id); const current = graph?.current_node === node.id; const state = mastered ? "Understood" : struggling ? "Needs practice" : current ? "Current" : "Up next"; return <li key={node.id} className="relative flex gap-4 pb-7 last:pb-0">{index < conceptNodes.length - 1 && <span className="absolute left-[13px] top-7 h-[calc(100%-4px)] border-l border-[#c8baa7]" />}<span className={`relative z-10 mt-0.5 h-7 w-7 shrink-0 rounded-full border-2 ${mastered ? "border-[var(--accent-mastery)] bg-[var(--accent-mastery)]" : struggling ? "border-[var(--accent-attention)] bg-[#ead8d2]" : current ? "border-[var(--accent-growth)] bg-[#d7e6de]" : "border-[#aa9d8c] bg-[var(--surface)]"}`} /><span><strong className="block text-sm font-medium">{node.label}</strong><span className="mt-0.5 block text-xs text-[var(--muted)]">{state}</span></span></li>; })}</ol><p className="mt-10 border-t border-[var(--border)] pt-5 text-xs leading-5 text-[var(--muted)]">Each step becomes clearer through practice, not speed.</p></aside>;
}
function EducatorMessage({ children }: { children: ReactNode }) { return <article className="animate-card-enter max-w-[92%]"><p className="mb-2 text-xs font-semibold uppercase tracking-[.13em] text-[var(--muted)]">Educator</p><div className="rounded-[1.4rem] rounded-tl-sm bg-white px-5 py-4 text-[var(--text-primary)] shadow-[0_2px_12px_rgba(36,28,21,.06)] sm:px-6">{children}</div></article>; }

function Subjects({ subjects, busy, onSelect }: { subjects: Subject[]; busy: boolean; onSelect: (subject: Subject) => void }) { return <><EducatorMessage><h1 className="tutor-display text-3xl font-semibold">What would you like to learn?</h1><p className="mt-3 leading-7">Choose a subject and I’ll begin by understanding your starting point.</p></EducatorMessage><div className="grid gap-3">{subjects.map((subject) => <button key={subject.id} disabled={busy} onClick={() => onSelect(subject)} className="animate-card-enter rounded-[1.35rem] border border-[var(--border)] bg-[#eee0c8] px-6 py-5 text-left transition hover:-translate-y-0.5 hover:shadow-md active:scale-[.99] disabled:opacity-60"><p className="text-xs font-semibold uppercase tracking-[.13em] text-[var(--muted)]">Subject 01</p><h2 className="tutor-display mt-2 text-3xl font-semibold">{subject.label}</h2><p className="mt-2 text-sm">Build algebra foundations one idea at a time. <span className="ml-2">→</span></p></button>)}</div></>; }
function Diagnostic({ question, number, busy, onSelect }: { question: DiagnosticQuestion; number: number; busy: boolean; onSelect: (option: string) => void }) { return <EducatorMessage><p className="text-sm text-[var(--muted)]">A quick starting point · {number} of 2</p><h1 className="tutor-display mt-1 text-3xl font-semibold">Let’s find a helpful place to begin.</h1><p className="mt-5 text-lg leading-8">{question.prompt}</p><div className="mt-6 grid gap-2">{question.options.map((option) => <button key={option.id} disabled={busy} onClick={() => onSelect(option.id)} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left text-sm transition hover:border-[var(--accent-mastery)] hover:bg-[#fffaf1] active:scale-[.99] disabled:opacity-60"><span className="mr-3 text-xs font-semibold text-[var(--accent-mastery)]">{option.id.toUpperCase()}</span>{option.text}</button>)}</div><p className="mt-5 text-sm leading-6 text-[var(--muted)]">This isn’t a mark. It helps me choose the right next step.</p></EducatorMessage>; }
function Checkin({ busy, onSelect }: { busy: boolean; onSelect: (checkin: Checkin) => void }) { const choices: { id: Checkin; title: string; copy: string }[] = [{ id: "confident", title: "I feel ready", copy: "Let’s get started." }, { id: "unsure", title: "I’m not sure yet", copy: "Take it one piece at a time." }, { id: "anxious", title: "I’m feeling worried", copy: "Keep it calm and manageable." }]; return <EducatorMessage><h1 className="tutor-display text-3xl font-semibold">How are you feeling about Maths today?</h1><p className="mt-3 leading-7">There’s no wrong choice. This helps me set the pace.</p><div className="mt-6 grid gap-2">{choices.map((choice) => <button key={choice.id} disabled={busy} onClick={() => onSelect(choice.id)} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left transition hover:border-[var(--accent-growth)] active:scale-[.99] disabled:opacity-60"><strong>{choice.title}</strong><span className="ml-2 text-sm text-[var(--muted)]">{choice.copy}</span></button>)}</div></EducatorMessage>; }
function Prerequisite({ check, busy, onSubmit }: { check: PrerequisiteCheck; busy: boolean; onSubmit: (multipleChoice: string, text: string) => void }) { const [selected, setSelected] = useState(""); const [text, setText] = useState(""); return <EducatorMessage><p className="text-sm text-[var(--muted)]">A small foundation check</p><h1 className="tutor-display mt-1 text-3xl font-semibold">Let’s make the next idea easier.</h1><p className="mt-5 text-lg leading-7">{check.multiple_choice.prompt}</p><div className="mt-5 grid gap-2">{check.multiple_choice.options.map((option) => <button key={option} onClick={() => setSelected(option)} className={`rounded-xl border px-4 py-3 text-left text-sm transition ${selected === option ? "border-[var(--bg-primary)] bg-[var(--bg-primary)] text-[var(--text-inverse)]" : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent-mastery)]"}`}>{option}</button>)}</div><label className="mt-7 block text-sm font-medium">{check.text_prompt}<textarea value={text} onChange={(event) => setText(event.target.value)} rows={3} className="mt-3 w-full resize-none rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-normal outline-none focus:border-[var(--accent-mastery)] focus:ring-2 focus:ring-[#c77d3c]/20" placeholder="Write what you think…" /></label><button disabled={busy || !selected || !text.trim()} onClick={() => onSubmit(selected, text.trim())} className="mt-5 rounded-full bg-[var(--accent-mastery)] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#ad682e] disabled:opacity-50">{busy ? "Checking…" : "Continue →"}</button></EducatorMessage>; }
function Teaching({ turn, note, pulse, busy, onCheck, onSignal }: { turn: TeachingTurn; note: string; pulse?: { recent_accuracy: number | null; accuracy_trend: string; pace_trend: string }; busy: boolean; onCheck: () => void; onSignal: (kind: "inactivity" | "struggling" | "challenge") => void }) { const prompt = pulse?.accuracy_trend === "declining" ? "Are you struggling to understand somewhere?" : (pulse?.recent_accuracy ?? 0) >= .75 && pulse?.pace_trend === "faster" ? "You’re moving quickly and accurately. Do you want more challenging questions?" : ""; return <EducatorMessage><p className="text-sm text-[var(--muted)]">Your lesson</p>{note && <p className="mt-3 rounded-xl bg-[#e4ece6] px-3 py-2 text-sm leading-5 text-[#395c50]">{note}</p>}{prompt && <div className="mt-3 rounded-xl border border-[var(--border)] p-3 text-sm"><p>{prompt}</p><button onClick={() => onSignal(pulse?.accuracy_trend === "declining" ? "struggling" : "challenge")} className="mt-3 rounded-full border border-[var(--border)] px-3 py-1.5">Yes</button></div>}<div className="mt-3 whitespace-pre-wrap text-lg leading-8">{turn.teaching_content}</div><div className="mt-7 border-t border-[var(--border)] pt-5"><button disabled={busy} onClick={onCheck} className="rounded-full bg-[var(--bg-primary)] px-5 py-2.5 text-sm font-medium text-[var(--text-inverse)] transition hover:bg-[#273d51] active:scale-[.98] disabled:opacity-60">Practice <span aria-hidden="true">→</span></button></div></EducatorMessage>; }
function Checks({ turn, answers, setAnswers, busy, onSubmit }: { turn: TeachingTurn; answers: string[]; setAnswers: (answers: string[]) => void; busy: boolean; onSubmit: () => void }) { return <EducatorMessage><p className="text-sm text-[var(--muted)]">A quick check-in</p><h1 className="tutor-display mt-1 text-3xl font-semibold">Show me how you’re thinking.</h1><p className="mt-3 leading-7">Use your own words. This guides what we do next.</p><div className="mt-7 grid gap-5">{turn.check_questions.map((question, index) => <label key={question} className="block text-sm font-medium">{question}<textarea value={answers[index] ?? ""} onChange={(event) => { const next = [...answers]; next[index] = event.target.value; setAnswers(next); }} rows={2} className="mt-2 w-full resize-none rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-normal outline-none focus:border-[var(--accent-mastery)] focus:ring-2 focus:ring-[#c77d3c]/20" placeholder="Type your answer…" /></label>)}</div><button disabled={busy || answers.some((answer) => !answer.trim())} onClick={onSubmit} className="mt-6 rounded-full bg-[var(--accent-mastery)] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#ad682e] disabled:opacity-50">{busy ? "Considering your answer…" : "Send answer →"}</button></EducatorMessage>; }
function VoiceReply({ result }: { result: VoiceDoubtResult }) { const affectLabel = { anxious: "Taking it gently", neutral: "A closer look", confident: "Following your curiosity" }[result.affect]; return <EducatorMessage><p className="text-xs font-semibold uppercase tracking-[.13em] text-[var(--accent-growth)]">{affectLabel}</p><p className="mt-3 whitespace-pre-wrap leading-7">{result.reply_text}</p><div className="mt-5 flex gap-2"><button onClick={() => { window.speechSynthesis?.cancel(); window.speechSynthesis?.speak(new SpeechSynthesisUtterance(result.reply_text)); }} className="rounded-full border border-[var(--border)] px-3 py-2 text-sm transition hover:bg-[var(--surface)]">Hear that again</button><button onClick={() => window.speechSynthesis?.cancel()} className="rounded-full px-3 py-2 text-sm text-[var(--muted)] underline">Stop</button></div></EducatorMessage>; }
function elapsedSeconds(startedAt: number) { return Math.max(0, (Date.now() - startedAt) / 1000); }
function noteForInstruction(ruleId: string) { return ({ high_stress_easy_win: "We’ll begin with one smaller step so this feels manageable.", struggling_prerequisite_recheck: "I’m revisiting the foundation once before we move on.", high_retry_more_scaffolding: "I’m slowing this down and adding a worked example.", mastery_stress_readiness_advance: "Your recent work suggests you’re ready to build on this.", resume_after_prerequisite_support: "We’ve checked the foundation, so we can return to the planned idea carefully." } as Record<string, string>)[ruleId] ?? "I’m continuing from the idea you were working on."; }
function messageFor(cause: unknown) { return cause instanceof Error ? cause.message : "We couldn’t complete that step. Please try again."; }
