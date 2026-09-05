import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-semibold text-text-primary">
        Warehouse AI Video Intelligence
      </h1>
      <p className="max-w-md text-text-muted">
        Supervisor console for reviewing detected warehouse behaviours, risk
        classification, and AI-assisted incident review.
      </p>
      <Link
        href="/dashboard"
        className="rounded-panel border border-border bg-surface px-5 py-2 text-sm font-medium text-text-primary transition-colors hover:border-accent"
      >
        Open dashboard
      </Link>
    </main>
  );
}