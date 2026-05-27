import {
  Badge,
  Body1,
  Button,
  Caption1,
  makeStyles,
  shorthands,
  Title1,
} from "@fluentui/react-components";
import {
  ArrowUploadRegular,
  BotRegular,
  DataTrendingRegular,
  DocumentDataRegular,
  FlashRegular,
  HistoryRegular,
} from "@fluentui/react-icons";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { listHistory } from "../api/client";
import { AgentTile } from "../components/dashboard/AgentTile";
import { PipelineFlow } from "../components/dashboard/PipelineFlow";
import { StatCard } from "../components/dashboard/StatCard";
import { MainPanel } from "../components/MainPanel";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { StatusBadge } from "../components/ui/StatusBadge";
import { AGENTS } from "../config/agents";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  hero: {
    position: "relative",
    ...shorthands.padding("28px", "32px"),
    borderRadius: "16px",
    marginBottom: "22px",
    backgroundColor: pulse.panelElevated,
    backgroundImage: `radial-gradient(900px 320px at 0% 0%, ${pulse.tealGlow}, transparent 65%), radial-gradient(700px 260px at 100% 100%, rgba(99,102,241,0.10), transparent 60%), linear-gradient(135deg, ${pulse.panelRaised} 0%, ${pulse.panelElevated} 60%, ${pulse.panel} 100%)`,
    border: `1px solid ${pulse.panelBorder}`,
    boxShadow: pulse.shadowSoft,
    overflow: "hidden",
  },
  heroBadgeRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "10px",
  },
  heroEyebrow: {
    fontSize: "10.5px",
    letterSpacing: "0.12em",
    color: pulse.tealBright,
    textTransform: "uppercase",
    fontWeight: 700,
  },
  heroTitle: {
    display: "block",
    fontSize: "30px",
    fontWeight: 700,
    color: pulse.text,
    marginBottom: "10px",
    letterSpacing: "-0.025em",
    lineHeight: 1.15,
    maxWidth: "720px",
  },
  heroSub: {
    display: "block",
    color: pulse.textMuted,
    maxWidth: "680px",
    lineHeight: 1.6,
    marginBottom: "18px",
    fontSize: "14px",
  },
  heroActions: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
  },
  grid4: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
    gap: "14px",
    marginBottom: "26px",
  },
  sectionHead: {
    display: "flex",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: "12px",
    marginBottom: "12px",
    marginTop: "8px",
  },
  sectionTitle: {
    display: "block",
    color: pulse.text,
    fontSize: "13px",
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
  },
  sectionHint: {
    color: pulse.textDim,
    fontSize: "12px",
  },
  agentGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: "14px",
    marginBottom: "26px",
  },
  twoCol: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: "20px",
    "@media (min-width: 1100px)": {
      gridTemplateColumns: "minmax(0, 1fr)",
    },
  },
  recentCard: {
    ...shorthands.padding("20px", "22px"),
    borderRadius: "14px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    boxShadow: pulse.shadowSoft,
  },
  mono: {
    fontFamily: pulse.fontMono,
    fontSize: "12px",
    color: pulse.tealBright,
  },
});

export function DashboardPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const historyQ = useQuery({ queryKey: ["history"], queryFn: listHistory });

  const runs = historyQ.data?.runs ?? [];
  const complete = runs.filter((r) => r.status === "complete").length;
  const running = runs.filter((r) => r.status === "running").length;
  const failed = runs.filter((r) => r.status === "failed").length;
  const recentColumns: DataTableColumn<(typeof runs)[number]>[] = [
    { key: "run", label: "Run", width: "18%", render: (r) => <span className={styles.mono}>{r.run_id.slice(0, 8)}…</span> },
    { key: "file", label: "File", width: "34%", render: (r) => r.filename ?? "(unnamed RFP)" },
    { key: "status", label: "Status", width: "16%", render: (r) => <StatusBadge status={r.status} /> },
    { key: "progress", label: "Progress", width: "12%", render: (r) => `${r.progress}%` },
    {
      key: "action",
      label: "Action",
      width: "20%",
      render: (r) => (
        <Button
          size="small"
          appearance="secondary"
          onClick={() => navigate(r.status === "complete" ? `/results/${r.run_id}` : `/analysis/${r.run_id}`)}
        >
          Open
        </Button>
      ),
    },
  ];

  return (
    <MainPanel title="Command center" subtitle="Multi-agent RFP intelligence platform">
      <div className={styles.hero}>
        <div className={styles.heroBadgeRow}>
          <Badge appearance="filled" color="brand" size="small">
            v2 · Multi-agent
          </Badge>
          <span className={styles.heroEyebrow}>Pre-sales workspace</span>
        </div>
        <Title1 className={styles.heroTitle}>
          Ship enterprise-grade RFP responses, end to end.
        </Title1>
        <Body1 className={styles.heroSub}>
          Five specialized agents orchestrated together — ingest documents, extract requirements,
          build executive summaries, generate clarifying questions, and draft a polished proposal
          with retrieval-grounded sections.
        </Body1>
        <div className={styles.heroActions}>
          <Button
            appearance="primary"
            size="large"
            icon={<ArrowUploadRegular />}
            onClick={() => navigate("/intake")}
          >
            New RFP intake
          </Button>
          <Button appearance="secondary" icon={<BotRegular />} onClick={() => navigate("/agents")}>
            Explore agent fleet
          </Button>
          <Button appearance="subtle" icon={<HistoryRegular />} onClick={() => navigate("/history")}>
            Run history
          </Button>
        </div>
      </div>

      <div className={styles.grid4}>
        <StatCard
          label="Pipeline runs"
          value={runs.length}
          sub="Sessions tracked across this workspace"
          icon={<DocumentDataRegular fontSize={20} />}
        />
        <StatCard
          label="Active"
          value={running}
          sub="Currently processing"
          accent={pulse.accentBlue}
          icon={<FlashRegular fontSize={20} />}
        />
        <StatCard
          label="Completed"
          value={complete}
          sub="Ready for results review"
          accent={pulse.success}
          icon={<DataTrendingRegular fontSize={20} />}
        />
        <StatCard
          label="Failed"
          value={failed}
          sub="Check Groq limits & logs"
          accent={pulse.danger}
          icon={<BotRegular fontSize={20} />}
        />
      </div>

      <div className={styles.sectionHead}>
        <Caption1 className={styles.sectionTitle}>Orchestration flow</Caption1>
        <span className={styles.sectionHint}>Stages run sequentially per RFP run</span>
      </div>
      <PipelineFlow progress={0} />

      <div className={styles.sectionHead} style={{ marginTop: 28 }}>
        <Caption1 className={styles.sectionTitle}>Agent fleet</Caption1>
        <span className={styles.sectionHint}>{AGENTS.length} specialized agents</span>
      </div>
      <div className={styles.agentGrid}>
        {AGENTS.map((agent) => (
          <AgentTile key={agent.id} agent={agent} />
        ))}
      </div>

      <div className={styles.twoCol} style={{ marginTop: 14 }}>
        <div className={styles.recentCard}>
          <div className={styles.sectionHead} style={{ marginTop: 0 }}>
            <Caption1 className={styles.sectionTitle}>Recent runs</Caption1>
            <Button size="small" appearance="subtle" onClick={() => navigate("/history")}>
              View all
            </Button>
          </div>
          {runs.length === 0 ? (
            <EmptyState
              title="No runs yet"
              description="Start with New RFP intake to populate recent pipeline activity."
              actionLabel="New RFP intake"
              onAction={() => navigate("/intake")}
            />
          ) : (
            <DataTable
              ariaLabel="Recent runs"
              rows={runs.slice(0, 6)}
              columns={recentColumns}
              getRowKey={(r) => r.run_id}
            />
          )}
        </div>
      </div>
    </MainPanel>
  );
}
