export function DashboardLoading({ message }: { message: string }) {
  return (
    <main className="grid min-h-screen place-items-center bg-[var(--canvas)] px-6 text-center">
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-[var(--soft-shadow)]">
        <p className="text-xl font-bold tracking-[-0.5px]">Mypedia</p>
        <p className="mt-4 max-w-sm text-[var(--muted)]">{message}</p>
      </div>
    </main>
  );
}
