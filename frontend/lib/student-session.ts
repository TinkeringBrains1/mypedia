export type StudentSession = { studentId: string; studentName: string; subjectId: string };

const sessionKey = "mypedia_student_session";

export function readStudentSession(): StudentSession | null {
  if (typeof window === "undefined") return null;
  // A demo checkpoint is valid only for the current browser tab. Keeping it
  // in localStorage can outlive a reset development database and point the
  // learner at a student id that no longer has Learning Memory.
  const raw = window.sessionStorage.getItem(sessionKey);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StudentSession;
  } catch {
    window.sessionStorage.removeItem(sessionKey);
    return null;
  }
}

export function saveStudentSession(session: StudentSession) {
  window.sessionStorage.setItem(sessionKey, JSON.stringify(session));
}

export function clearStudentSession() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(sessionKey);
  // Remove legacy checkpoints created before sessions were tab-scoped.
  window.localStorage.removeItem(sessionKey);
}
