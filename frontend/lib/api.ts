export type LearningMemoryApi = {
  student_id: string;
  subject_id: string;
  knowledge_profile: {
    mastery_score: number;
    concept_graph_position?: {
      current_node: string | null;
      mastered_nodes: string[];
      struggling_nodes: string[];
      not_yet_attempted_nodes: string[];
    };
  };
  cognitive_pacing_profile: {
    avg_response_latency_sec: number | null;
    hint_usage_rate: number;
    retry_rate: number;
  };
  affective_profile: {
    inferred: {
      engagement_score: number;
      stress_signal: number;
      stress_history: number[];
      self_efficacy_score: number;
    };
  };
  ai_desc: { summary: string };
  session_meta?: {
    lesson_pulse?: { recent_accuracy: number | null; accuracy_trend: "improving" | "steady" | "declining"; pace_trend: "faster" | "steady" | "slower" };
    paused_sessions?: { paused_at: string; topic: string; mastery_score: number; engagement_score: number; progress_summary: string }[];
  };
};

export type Subject = { id: string; label: string };
export type DiagnosticQuestion = {
  id: string;
  concept_node: string;
  prompt: string;
  options: { id: string; text: string }[];
};
export type DiagnosticResponse = {
  question_id: string;
  selected_option_id: string;
  response_latency_sec: number;
  used_hint: boolean;
  attempt_count: number;
};
export type TeachingTurn = {
  teaching_content: string;
  check_questions: string[];
};
export type StrategyInstructionApi = { rule_id: string; reason: string };
export type PrerequisiteCheck = {
  prerequisite_node: string;
  multiple_choice: { prompt: string; options: string[] };
  text_prompt: string;
};
export type PrerequisiteCheckResponse = {
  required: boolean;
  lesson_node: string;
  prerequisite_node: string | null;
  check: PrerequisiteCheck | null;
};
export type VoiceDoubtResult = {
  reply_text: string;
  affect: "anxious" | "neutral" | "confident";
  learning_memory: LearningMemoryApi;
};
export type CheckAnswer = {
  answer: string;
  response_latency_sec: number;
  used_hint: boolean;
  attempt_count: number;
};
export type CheckResponseResult = {
  learning_memory: LearningMemoryApi;
  lesson_complete: boolean;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Something went wrong. Please try again.");
  }
  return (await response.json()) as T;
}

export function getSubjects() {
  return request<Subject[]>("/subjects");
}

export function startDiagnostic(subjectId: string) {
  return request<{ diagnostic_session_id: string; question: DiagnosticQuestion }>(
    `/subjects/${encodeURIComponent(subjectId)}/diagnostic/start`, { method: "POST" },
  );
}

export function getNextDiagnosticQuestion(subjectId: string, diagnosticSessionId: string, response: DiagnosticResponse) {
  return request<{ question: DiagnosticQuestion }>(`/subjects/${encodeURIComponent(subjectId)}/diagnostic/next`, {
    method: "POST", body: JSON.stringify({ diagnostic_session_id: diagnosticSessionId, response }),
  });
}

export function submitDiagnostic(studentId: string, diagnosticSessionId: string, responses: DiagnosticResponse[], affectiveCheckin: "confident" | "unsure" | "anxious") {
  return request<{ learning_memory: LearningMemoryApi }>("/diagnostic", {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, diagnostic_session_id: diagnosticSessionId, submission: { responses, affective_checkin: affectiveCheckin } }),
  });
}

export function getLearningMemory(studentId: string, subjectId: string) {
  return request<LearningMemoryApi>(
    `/students/${encodeURIComponent(studentId)}/learning-memory?subject_id=${encodeURIComponent(subjectId)}`,
  );
}

export function getTeachingTurn(studentId: string, subjectId: string, previousTeachingContent?: string) {
  return request<{ teaching_turn: TeachingTurn; instruction: StrategyInstructionApi }>(
    `/students/${encodeURIComponent(studentId)}/teaching-turn?subject_id=${encodeURIComponent(subjectId)}`,
    { method: "POST", body: previousTeachingContent ? JSON.stringify({ previous_teaching_content: previousTeachingContent }) : undefined },
  );
}

export function getPrerequisiteCheck(studentId: string, subjectId: string) {
  return request<PrerequisiteCheckResponse>(
    `/students/${encodeURIComponent(studentId)}/prerequisite-check?subject_id=${encodeURIComponent(subjectId)}`,
    { method: "POST" },
  );
}

export function submitPrerequisiteCheck(
  studentId: string,
  subjectId: string,
  lessonNode: string,
  check: PrerequisiteCheck,
  multipleChoiceAnswer: string,
  textAnswer: string,
) {
  return request<{ lesson_ready: boolean; learning_memory: LearningMemoryApi }>(
    `/students/${encodeURIComponent(studentId)}/prerequisite-check-response?subject_id=${encodeURIComponent(subjectId)}`,
    {
      method: "POST",
      body: JSON.stringify({
        lesson_node: lessonNode,
        check,
        submission: {
          multiple_choice_answer: multipleChoiceAnswer,
          text_answer: textAnswer,
        },
      }),
    },
  );
}

export async function submitVoiceDoubt(
  studentId: string,
  subjectId: string,
  audio: Blob,
  activeContext: string,
): Promise<VoiceDoubtResult> {
  const form = new FormData();
  form.append("subject_id", subjectId);
  form.append("active_context", activeContext);
  form.append("audio", audio, `doubt.${extensionFor(audio.type)}`);
  const response = await fetch(`${apiBaseUrl}/students/${encodeURIComponent(studentId)}/voice-doubt`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "We could not hear that recording. Please try again.");
  }
  return (await response.json()) as VoiceDoubtResult;
}

function extensionFor(mimeType: string) {
  if (mimeType === "audio/ogg") return "ogg";
  if (mimeType === "audio/mp4") return "m4a";
  return "webm";
}

export function submitCheckResponse(studentId: string, subjectId: string, teachingTurn: TeachingTurn, answers: CheckAnswer[]) {
  return request<CheckResponseResult>(`/students/${encodeURIComponent(studentId)}/check-response`, {
    method: "POST",
    body: JSON.stringify({ subject_id: subjectId, teaching_turn: teachingTurn, submission: { answers } }),
  });
}

export function submitStudentSignal(studentId: string, subjectId: string, kind: "inactivity" | "struggling" | "challenge") {
  return request<LearningMemoryApi>(`/students/${encodeURIComponent(studentId)}/student-signal?subject_id=${encodeURIComponent(subjectId)}`, { method: "POST", body: JSON.stringify({ kind }) });
}

export function pauseSession(studentId: string, subjectId: string) {
  return request<LearningMemoryApi>(`/students/${encodeURIComponent(studentId)}/pause-session?subject_id=${encodeURIComponent(subjectId)}`, { method: "POST" });
}
