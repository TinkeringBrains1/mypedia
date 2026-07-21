"use client";

import { useEffect, useState } from "react";

import { DashboardLoading } from "../../components/dashboard-loading";
import { StudentDashboard } from "../../components/student-dashboard";
import { getLearningMemory, type LearningMemoryApi } from "../../lib/api";
import { readStudentSession } from "../../lib/student-session";

export default function SessionsPage() {
  const [memory, setMemory] = useState<LearningMemoryApi | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const session = readStudentSession();
    if (!session) { setError(true); return; }
    getLearningMemory(session.studentId, session.subjectId).then(setMemory).catch(() => setError(true));
  }, []);

  if (error) return <DashboardLoading message="No active student session is available. Start learning first, then return here." />;
  if (!memory) return <DashboardLoading message="Loading your sessions…" />;
  return <StudentDashboard memory={{ subjectId: memory.subject_id, sessions: memory.session_meta?.paused_sessions ?? [] }} onResume={() => { window.location.href = "/?continue=1"; }} />;
}
