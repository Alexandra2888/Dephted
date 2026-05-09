import Link from "next/link";
import { DepthedLogo } from "@/components/logo";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="mb-10">
        <DepthedLogo variant="wordmark-tagline" theme="dark" />
      </div>
      <div className="w-full max-w-sm flex flex-col gap-6 items-center">
        <h1 className="font-mono text-6xl font-semibold text-foreground tracking-tight">
          404_
        </h1>
        <p className="text-sm font-mono text-muted-foreground text-center">
          this page doesn&apos;t exist_
        </p>
        <Link
          href="/dashboard"
          className={cn(
            "h-10 px-5 rounded-md bg-foreground text-background",
            "text-sm font-mono font-medium",
            "hover:opacity-90 transition-opacity",
            "flex items-center justify-center",
          )}
        >
          back to dashboard_
        </Link>
      </div>
    </div>
  );
}
