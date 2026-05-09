export function LessonComplete() {
  return (
    <div className="mt-12 px-5 py-4 rounded-lg bg-success/[0.04] border border-success/[0.12] flex items-center gap-2.5">
      <span
        aria-hidden
        className="w-2 h-2 rounded-full bg-success shadow-[0_0_8px_hsl(var(--success))] shrink-0"
      />
      <span className="font-mono text-xs text-success">
        lesson complete — saved to your dashboard
      </span>
    </div>
  )
}
