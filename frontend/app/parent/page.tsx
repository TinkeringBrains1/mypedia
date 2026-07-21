"use client";

import { useEffect, useState } from "react";

import { DashboardLoading } from "../../components/dashboard-loading";
import { ParentDashboard } from "../../components/parent-dashboard";
import { getLearningMemory, type LearningMemoryApi } from "../../lib/api";
import { readStudentSession } from "../../lib/student-session";

export default function ParentDashboardPage() {
  const [memory, setMemory] = useState<LearningMemoryApi | null>(null);
  const [error, setError] = useState(false);
  const [studentName, setStudentName] = useState("");

  useEffect(() => {
    const session = readStudentSession();
    if (!session) {
      setError(true);
      return;
    }
    setStudentName(session.studentName);
    getLearningMemory(session.studentId, session.subjectId).then(setMemory).catch(() => setError(true));
  }, []);

  if (error) {
    return <DashboardLoading message="No active student session is available. Start learning first, then return here." />;
  }
  if (!memory) {
    return <DashboardLoading message="Loading the parent and teacher view…" />;
  }
  return <ParentDashboard memory={{ studentName, subjectId: memory.subject_id, masteryScore: memory.knowledge_profile.mastery_score, engagementScore: memory.affective_profile.inferred.engagement_score, stressSignal: memory.affective_profile.inferred.stress_signal, selfEfficacyScore: memory.affective_profile.inferred.self_efficacy_score, avgResponseLatencySec: memory.cognitive_pacing_profile.avg_response_latency_sec, hintUsageRate: memory.cognitive_pacing_profile.hint_usage_rate, retryRate: memory.cognitive_pacing_profile.retry_rate, aiDescription: memory.ai_desc.summary, stressHistory: memory.affective_profile.inferred.stress_history }} />;
}
