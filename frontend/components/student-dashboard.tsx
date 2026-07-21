import { LeftSidebar } from "./left-sidebar";

export type StudentDashboardMemory = {
  subjectId: string;
  sessions: {
    paused_at: string;
    topic: string;
    mastery_score: number;
    engagement_score: number;
    progress_summary: string;
  }[];
};

type StudentDashboardProps = {
  memory: StudentDashboardMemory;
  onResume: () => void;
};

function topicLabel(topic: string) {
  return topic.replace(/_/g, " ");
}

function formatPausedAt(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function StudentDashboard({ memory, onResume }: StudentDashboardProps) {
  const sessions = [...memory.sessions].reverse();
  return (
    <main className="min-h-screen bg-[var(--surface)] px-6 py-10 text-[var(--text-primary)] sm:px-10 lg:px-16 lg:pl-24">
      <div className="mx-auto max-w-3xl">
        <header className="border-b border-[var(--border)] pb-5">
          <p className="tutor-display text-3xl font-semibold">Mypedia</p>
          <p className="mt-1 text-sm text-[var(--muted)]">Your learning space</p>
        </header>
        <div className="mt-12">
          <p className="text-xs font-semibold uppercase tracking-[.14em] text-[var(--muted)]">Student dashboard</p>
          <h1 className="tutor-display mt-3 text-4xl font-semibold">Sessions</h1>
          <p className="mt-3 text-[var(--muted)]">Pick up from the concept you were working on.</p>
        </div>
        <section aria-label="Sessions" className="mt-8 space-y-3">
          {sessions.length === 0 ? <div className="rounded-2xl border border-[var(--border)] p-6 text-[var(--muted)]">No paused sessions yet.</div> : sessions.map((session, index) => (
            <article key={`${session.paused_at}-${index}`} className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--soft-shadow)]">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[.12em] text-[var(--muted)]">{formatPausedAt(session.paused_at)}</p><h2 className="tutor-display mt-2 text-2xl font-semibold capitalize">{topicLabel(session.topic)}</h2></div><button onClick={onResume} className="rounded-full bg-[var(--bg-primary)] px-4 py-2 text-sm text-[var(--text-inverse)] transition hover:bg-[#273d51]">Continue</button></div>
              <p className="mt-4 text-sm leading-6 text-[var(--muted)]">{session.progress_summary}</p>
            </article>
          ))}
        </section>
      </div>
      <LeftSidebar active="sessions" onLearn={onResume} />
    </main>
  );
}
