/** Ping FastAPI `/health` so a sleeping Render (or similar) dyno starts booting. */

function apiOrigin(): string | undefined {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (!raw) return undefined;
  return raw.replace(/\/$/, "");
}

export async function wakeBackend(timeoutMs = 60_000): Promise<void> {
  const origin = apiOrigin();
  if (!origin) return;

  const url = `${origin}/health`;
  const signal = AbortSignal.timeout(timeoutMs);

  try {
    await fetch(url, { method: "GET", cache: "no-store", signal });
  } catch {
    // Browser only: CORS or a cold-start abort. `no-cors` still hits Render.
    if (typeof window === "undefined") return;
    try {
      await fetch(url, {
        method: "GET",
        cache: "no-store",
        mode: "no-cors",
        signal,
      });
    } catch {
      // Ignore: the TCP hit is enough to start the machine.
    }
  }
}
