import { Body1, Caption1, makeStyles, shorthands } from "@fluentui/react-components";
import { useParams } from "react-router-dom";
import { AgentTile } from "../components/dashboard/AgentTile";
import { PipelineFlow } from "../components/dashboard/PipelineFlow";
import { MainPanel } from "../components/MainPanel";
import { AGENTS } from "../config/agents";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  intro: {
    ...shorthands.padding("20px", "24px"),
    borderRadius: "14px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    marginBottom: "24px",
    color: pulse.textMuted,
    lineHeight: 1.55,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
    gap: "18px",
  },
});

export function AgentsHubPage() {
  const styles = useStyles();
  const { runId } = useParams();

  return (
    <MainPanel
      title="Agent fleet"
      subtitle="Five specialized agents — each with its own workspace, inputs, and outputs"
      sessionId={runId}
    >
      <div className={styles.intro}>
        <Caption1
          style={{
            display: "block",
            color: pulse.teal,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontSize: "11px",
            fontWeight: 600,
          }}
        >
          Microsoft Agent Framework
        </Caption1>
        <Body1 style={{ display: "block", marginTop: 12, color: pulse.textMuted, lineHeight: 1.6 }}>
          The orchestrator routes your RFP through ingestion, understanding, summarization,
          clarification, and proposal drafting. Open any agent workspace to see what it does and
          inspect outputs for the active run.
        </Body1>
      </div>
      <PipelineFlow progress={0} />
      <Caption1 style={{ color: pulse.text, fontWeight: 600, margin: "28px 0 16px", display: "block" }}>
        All agents
      </Caption1>
      <div className={styles.grid}>
        {AGENTS.map((agent) => (
          <AgentTile key={agent.id} agent={agent} runId={runId} />
        ))}
      </div>
    </MainPanel>
  );
}
