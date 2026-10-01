"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { useWakeBackend } from "@/lib/hooks/use-wake-backend";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, refetchOnWindowFocus: false },
        },
      }),
  );
  useWakeBackend();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
