import Link from "next/link"
import { redirect } from "next/navigation"
import { BrandMark } from "@/components/shared/brand-mark"
import { createClient } from "@/lib/supabase/server"
import { NavUser } from "@/components/layout/nav-user"

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect("/login")

  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-14 border-b border-border flex items-center px-6 gap-6 shrink-0">
        <Link href="/dashboard" className="flex items-center">
          <BrandMark />
        </Link>
        <nav className="flex items-center gap-4 ml-2">
          <Link
            href="/dashboard"
            className="font-mono text-xs text-subtle-foreground hover:text-foreground transition-colors"
          >
            dashboard
          </Link>
          <Link
            href="/history"
            className="font-mono text-xs text-subtle-foreground hover:text-foreground transition-colors"
          >
            history
          </Link>
        </nav>
        <div className="flex-1" />
        <NavUser email={user.email ?? ""} />
      </header>
      <main className="flex-1 px-6 py-10 max-w-4xl mx-auto w-full">
        {children}
      </main>
    </div>
  )
}
