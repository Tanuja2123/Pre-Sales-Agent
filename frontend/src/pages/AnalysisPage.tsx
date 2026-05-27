import {
  Button,
  MessageBar,
  MessageBarBody,
  Spinner,
  makeStyles,
} from "@fluentui/react-components";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getRunStatus, isApiNotFound } from "../api/client";
import { ChatBubble } from "../components/ChatBubble";
import { FauxChatInput, MainPanel } from "../components/MainPanel";
import { PIPELINE_STAGES, pulse } from "../theme/pulseColors";

const AGENT_MESSAGES: Record<string, string> = {
  ingest: "Parsing your document and chunking text for retrieval…",
  understand: "Extracting structured requirements with MAF classification…",
  summarize: "Building an executive summary and bid posture…",
  clarify: "Generating client-ready clarifying questions…",
  draft: "Drafting your proposal with Groq (RAG-backed sections)…",
};

const useStyles = makeStyles({
  actions: {
    marginTop: "8px",
    display: "flex",
    gap: "12px",
    flexWrap: "wrap",
  },
  thinking: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    color: pulse.textMuted,
    marginTop: "8px",
  },
});

export function AnalysisPage() {
  const styles = useStyles();
  const { runId } = useParams();
  const navigate = useNavigate();

  const q = useQuery({
    queryKey: ["status", runId],
    queryFn: () => getRunStatus(runId!),
    enabled: Boolean(runId),
    retry: (failureCount, error) => {
      if (isApiNotFound(error)) return false;
      return failureCount < 2;
    },
    refetchInterval: (query) => {
      if (query.state.status === "error") return false;
      const s = query.state.data?.status;
      if (s === "complete" || s === "failed" || s === "aborted") return false;
      return 500;
    },
  });

  useEffect(() => {
    const s = q.data?.status;
    const done = s === "complete" || (s === "failed" && (q.data?.progress ?? 0) >= 100);
    if (done) navigate(`/results/${runId}`);
  }, [q.data?.status, q.data?.progress, navigate, runId]);

  const progress = q.data?.progress ?? 0;
  const status = q.data?.status ?? "";
  const failed = status === "failed" || status === "aborted";
  const runMissing = q.isError && isApiNotFound(q.error);

  const visibleStages = useMemo(() => {
    return PIPELINE_STAGES.filter((_stage, index) => {
      const prevTo = index > 0 ? PIPELINE_STAGES[index - 1].to : 0;
      return progress >= prevTo;
    });
  }, [progress]);

  if (!runId) {
    return (
      <MainPanel title="Pipeline" subtitle="Missing run id.">
        <ChatBubble role="bot">No session found. Start a new intake from the sidebar.</ChatBubble>
      </MainPanel>
    );
  }

  return (
    <MainPanel
      title="RFP pipeline"
      subtitle="Agents run sequentially — watch progress in the sidebar checklist."
      sessionId={runId}
      variant="chat"
      footer={
        <FauxChatInput
          placeholder={
            failed
              ? "Pipeline stopped — review error or start a new upload"
              : "Processing… results open automatically when complete"
          }
        />
      }
    >
      <ChatBubble role="user" avatarLabel="RFP">
        Started analysis for this session. Run the orchestrator on the uploaded document.
      </ChatBubble>

      {visibleStages.map((stage, index) => {
        const prevTo = index > 0 ? PIPELINE_STAGES[index - 1].to : 0;
        const done = progress >= stage.to;
        const active = progress >= prevTo && !done;
        return (
          <ChatBubble key={stage.id} role="bot">
            <strong>{stage.label}</strong>
            <br />
            {AGENT_MESSAGES[stage.id]}
            {done ? " ✓" : active ? " …" : ""}
          </ChatBubble>
        );
      })}

      {q.isLoading ? (
        <div className={styles.thinking}>
          <Spinner size="small" />
          <span>Connecting to pipeline…</span>
        </div>
      ) : null}

      {runMissing ? (
        <MessageBar intent="warning">
          <MessageBarBody>
            This run is no longer on the server (API may have restarted). Upload again from the sidebar.
          </MessageBarBody>
        </MessageBar>
      ) : null}

      {q.data?.error && q.data.status !== "complete" ? (
        <MessageBar intent="error">
          <MessageBarBody>{q.data.error}</MessageBarBody>
        </MessageBar>
      ) : null}
      {q.data?.error && q.data.status === "complete" ? (
        <MessageBar intent="warning">
          <MessageBarBody>{q.data.error}</MessageBarBody>
        </MessageBar>
      ) : null}

      <div className={styles.actions}>
        <Button
          appearance="primary"
          onClick={() => navigate(`/results/${runId}`)}
          disabled={!q.data || (q.data.status !== "complete" && q.data.status !== "failed" && q.data.status !== "aborted")}
        >
          Open results
        </Button>
        <Button appearance="secondary" onClick={() => navigate(`/run/${runId}/agents`)}>
          Agent workspaces
        </Button>
        <Button appearance="subtle" onClick={() => navigate("/intake")}>
          New intake
        </Button>
      </div>
    </MainPanel>
  );
}
