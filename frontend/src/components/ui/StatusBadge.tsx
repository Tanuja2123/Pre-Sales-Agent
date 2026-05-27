import { Badge } from "@fluentui/react-components";

type StatusBadgeProps = {
  status?: string | null;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const value = (status ?? "").toLowerCase();
  if (value === "complete") return <Badge appearance="filled" color="success">Complete</Badge>;
  if (value === "failed") return <Badge appearance="filled" color="danger">Failed</Badge>;
  if (value === "aborted") return <Badge appearance="filled" color="warning">Aborted</Badge>;
  if (value === "running") return <Badge appearance="tint" color="brand">Running</Badge>;
  if (value === "pending") return <Badge appearance="outline">Pending</Badge>;
  return <Badge appearance="outline">{status || "Unknown"}</Badge>;
}
