"use client"

import { createClient } from "@/lib/supabase/client"
import { useRouter } from "next/navigation"

export function NavUser({ email }: { email: string }) {
  const router = useRouter()

  async function signOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push("/login")
  }

  return (
    <div className="flex items-center gap-4">
      <span className="text-xs font-mono text-muted-foreground hidden sm:block">
        {email}
      </span>
      <button
        onClick={signOut}
        className="text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
      >
        sign out
      </button>
    </div>
  )
}
