import {
  Badge,
  Body1,
  Button,
  Caption1,
  Card,
  CardHeader,
  makeStyles,
  shorthands,
  Spinner,
  Subtitle2,
} from "@fluentui/react-components";
import { ArrowLeftRegular, ArrowRightRegular } from "@fluentui/react-icons";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { getRunOutput, getRunStatus } from "../api/client";
import { DraftBody } from "../components/DraftBody";
import { MainPanel } from "../components/MainPanel";
import { PageToolbar } from "../components/ui/PageToolbar";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { StatusBadge } from "../components/ui/StatusBadge";
import { AGENTS, agentWorkspacePath, getAgent, type AgentId } from "../config/agents";
import type { PipelineOutput, QuestionOut, RequirementOut } from "../types/output";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  hero: {
    display: "flex",
    gap: "16px",
    flexWrap: "wrap",
    ...shorthands.padding("18px"),
    borderRadius: "14px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    marginBottom: "18px",
  },
  icon: {
    width: "54px",
    height: "54px",
    borderRadius: "14px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  ioGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
    marginTop: "20px",
    "@media (max-width: 720px)": { gridTemplateColumns: "1fr" },
  },
  ioBox: {
    ...shorthands.padding("16px"),
    borderRadius: "10px",
    backgroundColor: pulse.panel,
    border: `1px solid ${pulse.panelBorder}`,
  },
  ioLabel: {
    display: "block",
    fontSize: "10px",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: pulse.textDim,
    marginBottom: "10px",
    fontWeight: 600,
  },
  outputPanel: {
    ...shorthands.padding("16px"),
    borderRadius: "14px",
    backgroundColor: pulse.panel,
    border: `1px solid ${pulse.panelBorder}`,
    marginTop: "16px",
  },
  sectionTitle: {
    display: "block",
    color: pulse.text,
    marginBottom: "12px",
  },
  sectionLine: {
    display: "block",
  },
  fieldLabel: {
    display: "block",
    color: pulse.textDim,
    fontSize: "11px",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    fontWeight: 600,
    marginTop: "16px",
    marginBottom: "6px",
  },
  pillRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "8px",
  },
  cardItem: {
    marginTop: "12px",
  },
  navRow: {
    display: "flex",
    justifyContent: "space-between",
    marginTop: "24px",
    flexWrap: "wrap",
    gap: "12px",
  },
});

function AgentOutput({ agentId, data }: { agentId: AgentId; data: PipelineOutput }) {
  const styles = useStyles();

  if (agentId === "ingest") {
    const chunkCount = data.rfp?.chunks?.length ?? 0;
    const sectionEntries = Object.entries(data.rfp?.sections ?? {});
    const sectionColumns: DataTableColumn<[string, string]>[] = [
      { key: "heading", label: "Heading", width: "30%", render: ([heading]) => <strong>{heading}</strong> },
      { key: "preview", label: "Preview", width: "70%", render: ([, preview]) => (preview ?? "").slice(0, 220) },
    ];
    return (
      <div className={styles.outputPanel}>
        <Subtitle2 as="h3" className={styles.sectionTitle}>
          Document ingested
        </Subtitle2>
        <Body1 as="p" className={styles.sectionLine} style={{ color: pulse.textMuted, margin: 0 }}>
          File: <strong style={{ color: pulse.text }}>{data.rfp?.filename ?? "—"}</strong>
        </Body1>
        <Body1 as="p" className={styles.sectionLine} style={{ color: pulse.textMuted, margin: "6px 0 0" }}>
          Document ID: <code style={{ color: pulse.text }}>{data.rfp?.document_id ?? "—"}</code>
        </Body1>

        <div className={styles.pillRow}>
          <Badge appearance="tint" color="informative">
            {chunkCount} chunks indexed
          </Badge>
          <Badge appearance="tint" color="informative">
            {sectionEntries.length} sections detected
          </Badge>
        </div>

        {sectionEntries.length > 0 ? (
          <>
            <Caption1 className={styles.fieldLabel}>Sections detected</Caption1>
            <DataTable
              ariaLabel="Sections"
              columns={sectionColumns}
              rows={sectionEntries}
              getRowKey={([heading]) => heading}
            />
          </>
        ) : null}

        {chunkCount > 0 ? (
          <>
            <Caption1 className={styles.fieldLabel}>Sample chunks</Caption1>
            {(data.rfp?.chunks ?? []).slice(0, 6).map((c, i) => (
              <Card key={c.chunk_id ?? i} appearance="outline" className={styles.cardItem}>
                <CardHeader
                  header={<Caption1 style={{ color: pulse.textDim }}>{c.chunk_id}</Caption1>}
                  description={
                    <Body1 style={{ color: pulse.textMuted }}>
                      {(c.text ?? "").slice(0, 360)}
                      {(c.text ?? "").length > 360 ? "…" : ""}
                    </Body1>
                  }
                />
              </Card>
            ))}
          </>
        ) : null}
      </div>
    );
  }

  if (agentId === "understand") {
    const reqs = (data.requirements ?? []) as RequirementOut[];
    const reqColumns: DataTableColumn<RequirementOut>[] = [
      { key: "id", label: "ID", width: "9%", render: (r) => r.requirement_id ?? "—" },
      { key: "type", label: "Type", width: "12%", render: (r) => r.type ?? "—" },
      { key: "priority", label: "Priority", width: "12%", render: (r) => r.priority ?? "—" },
      { key: "maf", label: "MAF", width: "8%", render: (r) => r.maf_classification ?? "—" },
      { key: "section", label: "Section", width: "14%", render: (r) => r.source_section ?? "—" },
      { key: "text", label: "Text", width: "38%", render: (r) => r.text ?? "" },
      { key: "amb", label: "Ambig.", width: "7%", render: (r) => r.ambiguity_score ?? "—" },
    ];
    return (
      <div className={styles.outputPanel}>
        <Subtitle2 className={styles.sectionTitle}>{reqs.length} requirements extracted</Subtitle2>
        {reqs.length === 0 ? (
          <Body1 style={{ color: pulse.textMuted }}>No requirements extracted.</Body1>
        ) : (
          <DataTable
            ariaLabel="Extracted requirements"
            columns={reqColumns}
            rows={reqs}
            getRowKey={(r, idx) => r.requirement_id ?? `req-${idx}`}
          />
        )}
      </div>
    );
  }

  if (agentId === "summarize" && data.summary) {
    const s = data.summary;
    return (
      <div className={styles.outputPanel}>
        <Subtitle2 className={styles.sectionTitle}>Executive summary</Subtitle2>

        <Caption1 className={styles.fieldLabel}>Go / no-go</Caption1>
        <Body1 style={{ color: pulse.teal }}>{s.go_no_go_recommendation ?? "—"}</Body1>

        <Caption1 className={styles.fieldLabel}>Client overview</Caption1>
        <Body1 style={{ color: pulse.textMuted }}>{s.client_overview ?? "—"}</Body1>

        <Caption1 className={styles.fieldLabel}>Strategic objectives</Caption1>
        <Body1 style={{ color: pulse.textMuted }}>{s.strategic_objectives ?? "—"}</Body1>

        <Caption1 className={styles.fieldLabel}>Evaluation criteria</Caption1>
        <Body1 style={{ color: pulse.textMuted }}>{s.evaluation_criteria ?? "—"}</Body1>

        <Caption1 className={styles.fieldLabel}>Bid strategy</Caption1>
        <Body1 style={{ color: pulse.textMuted }}>{s.bid_strategy ?? "—"}</Body1>

        {(s.key_requirements ?? []).length > 0 ? (
          <>
            <Caption1 className={styles.fieldLabel}>Key requirements</Caption1>
            <ul style={{ color: pulse.textMuted, paddingLeft: 20, margin: 0 }}>
              {(s.key_requirements ?? []).map((k, i) => (
                <li key={i}>{k}</li>
              ))}
            </ul>
          </>
        ) : null}

        {(s.risk_flags ?? []).length > 0 ? (
          <>
            <Caption1 className={styles.fieldLabel}>Risk flags</Caption1>
            <ul style={{ color: pulse.textMuted, paddingLeft: 20, margin: 0 }}>
              {(s.risk_flags ?? []).map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
    );
  }

  if (agentId === "clarify") {
    const qs = (data.questions ?? []) as QuestionOut[];
    return (
      <div className={styles.outputPanel}>
        <Subtitle2 className={styles.sectionTitle}>{qs.length} clarifying questions</Subtitle2>
        {qs.length === 0 ? (
          <Body1 style={{ color: pulse.textMuted }}>No questions generated.</Body1>
        ) : (
          qs.map((q) => (
            <Card key={q.question_id} appearance="outline" className={styles.cardItem}>
              <CardHeader
                header={
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    <Subtitle2 style={{ color: pulse.text }}>{q.question_text}</Subtitle2>
                    {q.category ? <Badge appearance="tint">{q.category}</Badge> : null}
                    {q.priority ? (
                      <Badge appearance="outline" color="brand">
                        {q.priority}
                      </Badge>
                    ) : null}
                  </div>
                }
                description={
                  <div style={{ marginTop: 8 }}>
                    {q.source_requirement ? (
                      <Caption1 style={{ color: pulse.textDim, display: "block" }}>
                        Source: {q.source_requirement}
                      </Caption1>
                    ) : null}
                    {q.assumption_if_unanswered ? (
                      <Body1 style={{ color: pulse.textMuted, marginTop: 6 }}>
                        <strong style={{ color: pulse.text }}>If unanswered: </strong>
                        {q.assumption_if_unanswered}
                      </Body1>
                    ) : null}
                  </div>
                }
              />
            </Card>
          ))
        )}
      </div>
    );
  }

  if (agentId === "draft") {
    const sections = data.draft_response?.sections ?? [];
    return (
      <div className={styles.outputPanel}>
        <Subtitle2 className={styles.sectionTitle}>{sections.length} proposal sections</Subtitle2>
        {sections.length === 0 ? (
          <Body1 style={{ color: pulse.textMuted }}>Draft is empty.</Body1>
        ) : (
          <div
            style={{
              marginTop: 16,
              padding: "28px 32px",
              borderRadius: 12,
              border: `1px solid ${pulse.panelBorder}`,
              backgroundColor: pulse.panelElevated,
            }}
          >
            {sections.map((sec) => (
              <DraftBody key={sec.section_id} body={sec.body ?? ""} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <Body1 style={{ color: pulse.textMuted }}>
      Output not available yet — wait for the pipeline to complete this stage.
    </Body1>
  );
}

export function AgentWorkspacePage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { agentId, runId } = useParams<{ agentId: string; runId?: string }>();
  const agent = agentId ? getAgent(agentId) : undefined;

  const statusQ = useQuery({
    queryKey: ["status", runId],
    queryFn: () => getRunStatus(runId!),
    enabled: Boolean(runId),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      if (s === "complete" || s === "failed" || s === "aborted") return false;
      return 800;
    },
  });

  const outputQ = useQuery({
    queryKey: ["output", runId],
    queryFn: () => getRunOutput(runId!),
    enabled:
      Boolean(runId) &&
      (statusQ.data?.status === "complete" ||
        statusQ.data?.status === "failed" ||
        statusQ.data?.status === "aborted"),
    retry: false,
  });

  if (!agent) {
    return <Navigate to="/agents" replace />;
  }

  const Icon = agent.Icon;
  const progress = statusQ.data?.progress ?? (outputQ.data ? 100 : 0);
  const idx = AGENTS.findIndex((a) => a.id === agent.id);
  const prev = idx > 0 ? AGENTS[idx - 1] : null;
  const next = idx < AGENTS.length - 1 ? AGENTS[idx + 1] : null;
  const done = progress >= agent.progressTo;
  const prevTo = idx > 0 ? AGENTS[idx - 1].progressTo : 0;
  const active = progress >= prevTo && progress < agent.progressTo;

  const showOutput = Boolean(runId && outputQ.data);

  return (
    <MainPanel title={agent.name} subtitle={agent.tagline} sessionId={runId}>
      <PageToolbar
        meta={runId ? `Run ${runId.slice(0, 8)} · ${Math.round(progress)}% pipeline progress` : "Catalog mode"}
        left={<StatusBadge status={done ? "complete" : active ? "running" : "pending"} />}
        right={
          <>
            <Button appearance="secondary" onClick={() => navigate("/agents")}>
              Agent fleet
            </Button>
            {runId && statusQ.data?.status === "complete" ? (
              <Button appearance="primary" onClick={() => navigate(`/results/${runId}`)}>
                Full results
              </Button>
            ) : null}
          </>
        }
      />
      <div className={styles.hero}>
        <div className={styles.icon} style={{ backgroundColor: `${agent.accent}22`, color: agent.accent }}>
          <Icon fontSize={32} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            {active ? (
              <StatusBadge status="running" />
            ) : null}
            {done ? (
              <StatusBadge status="complete" />
            ) : null}
            {!runId ? <Badge appearance="outline">Catalog mode</Badge> : null}
          </div>
          <Body1 style={{ display: "block", color: pulse.textMuted, lineHeight: 1.6, fontSize: "14px" }}>
            {agent.description}
          </Body1>
          <div className={styles.ioGrid}>
            <div className={styles.ioBox}>
              <Caption1 className={styles.ioLabel}>Inputs</Caption1>
              <ul style={{ margin: 0, paddingLeft: 18, color: pulse.textMuted, fontSize: 13 }}>
                {agent.inputs.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            </div>
            <div className={styles.ioBox}>
              <Caption1 className={styles.ioLabel}>Outputs</Caption1>
              <ul style={{ margin: 0, paddingLeft: 18, color: pulse.textMuted, fontSize: 13 }}>
                {agent.outputs.map((o) => (
                  <li key={o}>{o}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {runId && statusQ.isLoading ? <Spinner label="Loading run status…" /> : null}

      {runId && !showOutput && statusQ.data?.status === "running" ? (
        <Body1 style={{ color: pulse.textMuted }}>
          Pipeline at {progress}% — this agent&apos;s output will appear when its stage completes.
        </Body1>
      ) : null}

      {showOutput && outputQ.data ? <AgentOutput agentId={agent.id} data={outputQ.data} /> : null}

      {runId && statusQ.data?.status === "complete" && !showOutput && !outputQ.isLoading ? (
        <Button appearance="primary" onClick={() => navigate(`/results/${runId}`)}>
          View full pipeline results
        </Button>
      ) : null}

      <div className={styles.navRow}>
        <Button appearance="subtle" icon={<ArrowLeftRegular />} onClick={() => navigate("/agents")}>
          Agent fleet
        </Button>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {prev ? (
            <Button appearance="secondary" onClick={() => navigate(agentWorkspacePath(prev.id, runId))}>
              ← {prev.shortName}
            </Button>
          ) : null}
          {next ? (
            <Button
              appearance="primary"
              icon={<ArrowRightRegular />}
              iconPosition="after"
              onClick={() => navigate(agentWorkspacePath(next.id, runId))}
            >
              {next.shortName}
            </Button>
          ) : null}
          {runId && statusQ.data?.status === "complete" ? (
            <Button appearance="secondary" onClick={() => navigate(`/results/${runId}`)}>
              Full results
            </Button>
          ) : null}
        </div>
      </div>
    </MainPanel>
  );
}
