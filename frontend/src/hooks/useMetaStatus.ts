import { useQuery } from "@tanstack/react-query";
import { getMetaStatus } from "@/lib/api";

export function useMetaStatus() {
  const statusQuery = useQuery({
    queryKey: ["meta-status"],
    queryFn: getMetaStatus,
    retry: 1,
    refetchInterval: 60 * 1000,
  });

  return {
    status: statusQuery.data,
    isLoading: statusQuery.isLoading,
    isError: statusQuery.isError,
  };
}
