"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { userApi } from "@/lib/api/sessions";
import { TopicGridClient } from "./topic-grid-client";
import type { DashboardData } from "@/lib/types";

export function DashboardGrid({
  initialData,
  fetchedAt,
}: {
  initialData: DashboardData;
  fetchedAt: number;
}) {
  const queryClient = useQueryClient();

  const cachedAt =
    queryClient.getQueryState<DashboardData>(["dashboard"])?.dataUpdatedAt ?? 0;
  if (fetchedAt > cachedAt) {
    queryClient.setQueryData(["dashboard"], initialData, {
      updatedAt: fetchedAt,
    });
  }

  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: userApi.memory,
    initialData,
    initialDataUpdatedAt: fetchedAt,
  });
  return (
    <TopicGridClient suggested={data.suggested_next} topics={data.topics} />
  );
}
