import { Button, Caption1, makeStyles, Spinner, Text, tokens, Tooltip } from "@fluentui/react-components";
import {
  ArrowClockwiseRegular,
  DeleteRegular,
  DocumentRegular,
  DocumentSearchRegular,
} from "@fluentui/react-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { deleteRun, listHistory, type HistoryRun } from "../api/client";
import { MainPanel } from "../components/MainPanel";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { PageToolbar } from "../components/ui/PageToolbar";
import { StatusBadge } from "../components/ui/StatusBadge";

const useStyles = makeStyles({
  toolbar: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
    marginBottom: tokens.spacingVerticalL,
  },
  toolbarMeta: {
    marginLeft: "auto",
    color: tokens.colorNeutralForeground3,
  },
  emptyWrap: {
    marginTop: tokens.spacingVerticalXL,
    display: "flex",
    justifyContent: "center",
  },
  mono: {
    fontFamily: tokens.fontFamilyMonospace,
    fontSize: tokens.fontSizeBase200,
  },
  fileCell: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    minWidth: 0,
  },
  fileName: {
    fontWeight: tokens.fontWeightSemibold,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    maxWidth: "260px",
  },
  metaLine: {
    display: "block",
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase200,
  },
  rowActions: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    flexWrap: "wrap",
  },
});

function formatWhen(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatDuration(seconds?: number | null): string {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function shortId(id: string): string {
  if (!id) return "—";
  return id.length > 13 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}

export function HistoryPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["history"],
    queryFn: listHistory,
    refetchOnWindowFocus: true,
  });

  const removeM = useMutation({
    mutationFn: (runId: string) => deleteRun(runId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["history"] });
    },
  });

  const runs: HistoryRun[] = q.data?.runs ?? [];
  const total = q.data?.count ?? runs.length;
  const columns: DataTableColumn<HistoryRun>[] = [
    {
      key: "rfp",
      label: "RFP",
      width: "28%",
      render: (r) => (
        <div className={styles.fileCell}>
          <DocumentRegular />
          <div style={{ minWidth: 0 }}>
            <Tooltip content={r.filename ?? "Unknown filename"} relationship="label">
              <Text className={styles.fileName}>{r.filename || "(unnamed RFP)"}</Text>
            </Tooltip>
            {r.error ? (
              <Caption1 className={styles.metaLine} style={{ color: tokens.colorPaletteRedForeground1 }}>
                {r.error}
              </Caption1>
            ) : null}
          </div>
        </div>
      ),
    },
    { key: "status", label: "Status", width: "12%", render: (r) => <StatusBadge status={r.status} /> },
    { key: "progress", label: "Progress", width: "10%", render: (r) => <Text weight="semibold">{r.progress}%</Text> },
    { key: "started", label: "Started", width: "17%", render: (r) => formatWhen(r.started_at ?? r.created_at) },
    { key: "duration", label: "Duration", width: "10%", render: (r) => formatDuration(r.duration_seconds) },
    {
      key: "runId",
      label: "Run ID",
      width: "11%",
      render: (r) => (
        <Tooltip content={r.run_id} relationship="label">
          <Text className={styles.mono}>{shortId(r.run_id)}</Text>
        </Tooltip>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      width: "12%",
      render: (r) => (
        <div className={styles.rowActions}>
          <Button size="small" onClick={() => navigate(`/results/${r.run_id}`)}>
            Results
          </Button>
          <Button size="small" appearance="subtle" onClick={() => navigate(`/analysis/${r.run_id}`)}>
            Status
          </Button>
          <Tooltip content="Delete run permanently" relationship="label">
            <Button
              size="small"
              appearance="subtle"
              icon={<DeleteRegular />}
              aria-label="Delete run"
              disabled={removeM.isPending}
              onClick={() => {
                if (window.confirm(`Delete run ${shortId(r.run_id)}? This cannot be undone.`)) {
                  removeM.mutate(r.run_id);
                }
              }}
            />
          </Tooltip>
        </div>
      ),
    },
  ];

  return (
    <MainPanel
      title="Run history"
      subtitle="Every RFP run is persisted to disk and survives server restarts."
    >
      <PageToolbar
        meta={total > 0 ? `${total} run${total === 1 ? "" : "s"} stored` : undefined}
        left={<Caption1 className={styles.toolbarMeta}>Review, reopen, or clean up historical RFP runs.</Caption1>}
        right={
          <>
            <Button icon={<ArrowClockwiseRegular />} appearance="secondary" onClick={() => void q.refetch()} disabled={q.isFetching}>
              Refresh
            </Button>
            <Button appearance="primary" onClick={() => navigate("/intake")}>
              New intake
            </Button>
          </>
        }
      />

      {q.isLoading ? (
        <div style={{ padding: tokens.spacingVerticalXXL }}>
          <Spinner size="large" label="Loading runs…" />
        </div>
      ) : null}

      {q.isError ? (
        <Text style={{ color: tokens.colorPaletteRedForeground1 }}>Could not load history.</Text>
      ) : null}

      {!q.isLoading && runs.length === 0 ? (
        <div className={styles.emptyWrap}>
          <EmptyState
            icon={<DocumentSearchRegular />}
            title="No runs yet"
            description="Upload an RFP from the sidebar. Completed runs are saved and will appear here."
            actionLabel="Go to upload"
            onAction={() => navigate("/intake")}
          />
        </div>
      ) : null}

      {runs.length > 0 ? (
        <DataTable
          ariaLabel="Run history"
          rows={runs}
          columns={columns}
          getRowKey={(r, i) => r.run_id ?? `run-${i}`}
        />
      ) : null}
    </MainPanel>
  );
}
