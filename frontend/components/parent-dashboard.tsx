import { LeftSidebar } from "./left-sidebar";

export type ParentDashboardMemory = {
  studentName: string;
  subjectId: string;
  masteryScore: number;
  engagementScore: number;
  stressSignal: number;
  selfEfficacyScore: number;
  avgResponseLatencySec: number | null;
  hintUsageRate: number;
  retryRate: number;
  aiDescription: string;
  stressHistory: number[];
};

type ParentDashboardProps = {
  memory: ParentDashboardMemory;
};

function percent(value: number) {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

function subjectLabel(subjectId: string) {
  return subjectId.replace(/_/g, " ");
}

function Metric({ label, value, helper, accent }: { label: string; value: string; helper: string; accent: string }) {
  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
      <p className="text-sm font-semibold text-[var(--muted)]">{label}</p>
      <p className="mt-3 text-3xl font-bold tracking-[-0.05em]" style={{ color: accent }}>
        {value}
      </p>
      <p className="mt-2 text-sm leading-5 text-[var(--muted)]">{helper}</p>
    </section>
  );
}

function StressTrend({ values }: { values: number[] }) {
  const safeValues = values.length ? values : [0];
  const coordinates = safeValues.map((value, index) => {
    const x = safeValues.length === 1 ? 8 : 8 + (index / (safeValues.length - 1)) * 264;
    const y = 90 - Math.max(0, Math.min(1, value)) * 74;
    return `${x},${y}`;
  });

  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--soft-shadow)]">
      <div className="flex items-baseline justify-between gap-4">
        <div>
        <h2 className="text-xl font-semibold tracking-[-0.125px]">Stress trend</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Signals recorded across recent learning checks.</p>
        </div>
        <span className="text-sm font-semibold text-[#b5474c]">Current {percent(safeValues[safeValues.length - 1] ?? 0)}%</span>
      </div>
      <svg aria-label="Stress trend chart" className="mt-8 h-28 w-full" role="img" viewBox="0 0 280 100">
        <line x1="8" x2="272" y1="16" y2="16" stroke="#f1e2e3" strokeDasharray="4 6" />
        <line x1="8" x2="272" y1="53" y2="53" stroke="#f1e2e3" strokeDasharray="4 6" />
        <line x1="8" x2="272" y1="90" y2="90" stroke="#f1e2e3" strokeDasharray="4 6" />
        <polyline fill="none" points={coordinates.join(" ")} stroke="#c9515a" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        {coordinates.map((coordinate) => {
          const [cx, cy] = coordinate.split(",");
          return <circle key={coordinate} cx={cx} cy={cy} fill="#c9515a" r="4" />;
        })}
      </svg>
    </section>
  );
}

export function ParentDashboard({ memory }: ParentDashboardProps) {
  return (
    <main className="min-h-screen bg-[var(--surface)] px-6 py-10 text-[var(--text-primary)] sm:px-10 lg:pl-[318px] lg:pr-16">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-6">
          <p className="tutor-display text-2xl font-semibold">Mypedia</p>
          <div className="text-right">
            <p className="font-semibold">{memory.studentName}</p>
            <p className="text-sm capitalize text-[var(--muted)]">{subjectLabel(memory.subjectId)}</p>
          </div>
        </header>

        <div className="mt-12 max-w-3xl">
          <p className="text-xs font-semibold tracking-[0.125px] text-[var(--primary)]">Parent & teacher view</p>
          <h1 className="tutor-display mt-3 text-4xl font-semibold sm:text-5xl">The signals behind the learning.</h1>
          <p className="mt-5 text-lg leading-8 text-[var(--muted)]">A focused view of academic progress, pacing, and wellbeing.</p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Mastery" value={`${percent(memory.masteryScore)}%`} helper="Current topic understanding" accent="#167a58" />
          <Metric label="Engagement" value={`${percent(memory.engagementScore)}%`} helper="Observed learning engagement" accent="#5d55d7" />
          <Metric label="Stress signal" value={`${percent(memory.stressSignal)}%`} helper="Current inferred support signal" accent="#c9515a" />
          <Metric label="Self-efficacy" value={`${percent(memory.selfEfficacyScore)}%`} helper="Confidence in problem-solving" accent="#bd7a14" />
          <Metric label="Response pace" value={memory.avgResponseLatencySec === null ? "—" : `${Math.round(memory.avgResponseLatencySec)}s`} helper="Average time to respond" accent="#276b9a" />
          <Metric label="Hint use" value={`${percent(memory.hintUsageRate)}%`} helper="Checks using a hint" accent="#276b9a" />
          <Metric label="Retry rate" value={`${percent(memory.retryRate)}%`} helper="Checks needing another attempt" accent="#276b9a" />
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-xl bg-[var(--secondary)] p-7 text-white shadow-[var(--soft-shadow)]">
            <p className="text-xs font-semibold tracking-[0.125px] text-[#d6b6f6]">Mypedia reflection</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight">Current learning picture</h2>
            <p className="mt-5 text-lg leading-8 text-[#e0ebe4]">
              {memory.aiDescription || "A learning reflection will appear after the next scheduled update."}
            </p>
          </section>
          <StressTrend values={memory.stressHistory} />
        </div>
      </div>
      <LeftSidebar active="parent" />
    </main>
  );
}
