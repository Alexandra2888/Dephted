"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { cn } from "@/lib/utils"

export function SignupForm() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.signUp({ email, password })
    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }
    router.push("/dashboard")
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
          email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={cn(
            "h-10 rounded-md border border-border bg-card px-3",
            "text-sm font-mono text-foreground",
            "focus:outline-none focus:border-foreground/40",
            "transition-colors"
          )}
          placeholder="you@example.com"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
          password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          className={cn(
            "h-10 rounded-md border border-border bg-card px-3",
            "text-sm font-mono text-foreground",
            "focus:outline-none focus:border-foreground/40",
            "transition-colors"
          )}
          placeholder="••••••••"
        />
      </div>

      {error && (
        <p className="text-xs font-mono text-destructive">{error}</p>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading}
        className={cn(
          "h-10 rounded-md bg-foreground text-background",
          "text-sm font-mono font-medium",
          "hover:opacity-90 transition-opacity",
          "disabled:opacity-40"
        )}
      >
        {loading ? "creating account_" : "create account_"}
      </button>

      <p className="text-xs font-mono text-muted-foreground text-center">
        have an account?{" "}
        <a href="/login" className="text-foreground hover:underline">
          sign in
        </a>
      </p>
    </div>
  )
}
