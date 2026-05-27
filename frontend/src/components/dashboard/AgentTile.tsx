import { Body1, Button, Caption1, makeStyles, shorthands, Title3 } from "@fluentui/react-components";
import { ArrowRightRegular } from "@fluentui/react-icons";
import { useNavigate } from "react-router-dom";
import type { AgentDefinition } from "../../config/agents";
import { agentWorkspacePath } from "../../config/agents";
import { pulse } from "../../theme/pulseColors";

const useStyles = makeStyles({
  card: {
    position: "relative",
    ...shorthands.padding("18px", "20px", "16px"),
    borderRadius: "14px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    height: "100%",
    cursor: "pointer",
    transition: "transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease",
    overflow: "hidden",
    boxShadow: pulse.shadowSoft,
    ":hover": {
      transform: "translateY(-2px)",
      boxShadow: pulse.shadowLift,
      borderTopColor: pulse.panelBorderStrong,
      borderRightColor: pulse.panelBorderStrong,
      borderBottomColor: pulse.panelBorderStrong,
      borderLeftColor: pulse.panelBorderStrong,
    },
  },
  accentEdge: {
    position: "absolute",
    top: 0,
    left: 0,
    bottom: 0,
    width: "3px",
  },
  head: {
    display: "flex",
    alignItems: "flex-start",
    gap: "14px",
  },
  icon: {
    width: "44px",
    height: "44px",
    borderRadius: "12px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    border: `1px solid ${pulse.panelBorder}`,
  },
  titleText: {
    display: "block",
    color: pulse.text,
    fontSize: "16px",
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: "-0.005em",
  },
  tagline: {
    display: "block",
    fontSize: "10.5px",
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    marginTop: "6px",
    fontWeight: 700,
  },
  desc: {
    display: "block",
    color: pulse.textMuted,
    fontSize: "13px",
    lineHeight: 1.55,
    flex: 1,
  },
  headText: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  meta: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap",
    marginTop: "4px",
  },
  pill: {
    fontSize: "10.5px",
    ...shorthands.padding("4px", "9px"),
    borderRadius: "999px",
    backgroundColor: pulse.panel,
    border: `1px solid ${pulse.panelBorder}`,
    color: pulse.textMuted,
    fontWeight: 600,
    letterSpacing: "0.02em",
  },
  footerRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "8px",
    marginTop: "4px",
  },
  stepBadge: {
    fontFamily: pulse.fontMono,
    fontSize: "10.5px",
    color: pulse.textDim,
    backgroundColor: pulse.panel,
    border: `1px solid ${pulse.panelBorder}`,
    borderRadius: "999px",
    padding: "2px 8px",
    letterSpacing: "0.04em",
  },
});

type AgentTileProps = {
  agent: AgentDefinition;
  runId?: string;
  done?: boolean;
  active?: boolean;
};

export function AgentTile({ agent, runId, done, active }: AgentTileProps) {
  const styles = useStyles();
  const navigate = useNavigate();
  const Icon = agent.Icon;

  return (
    <div
      className={styles.card}
      role="button"
      tabIndex={0}
      onClick={() => navigate(agentWorkspacePath(agent.id, runId))}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          navigate(agentWorkspacePath(agent.id, runId));
        }
      }}
      style={{
        borderColor: active ? agent.accent : done ? `${agent.accent}66` : undefined,
        boxShadow: active ? `0 0 0 1px ${agent.accent}55, ${pulse.shadowLift}` : undefined,
      }}
    >
      <div
        className={styles.accentEdge}
        style={{ background: `linear-gradient(180deg, ${agent.accent} 0%, ${agent.accent}33 100%)` }}
      />
      <div className={styles.head}>
        <div
          className={styles.icon}
          style={{
            backgroundColor: `${agent.accent}1f`,
            color: agent.accent,
            borderColor: `${agent.accent}40`,
          }}
        >
          <Icon fontSize={22} />
        </div>
        <div className={styles.headText}>
          <Title3 className={styles.titleText}>{agent.shortName}</Title3>
          <Caption1 className={styles.tagline} style={{ color: agent.accent }}>
            {agent.tagline}
          </Caption1>
        </div>
      </div>
      <Body1 className={styles.desc}>{agent.description}</Body1>
      <div className={styles.meta}>
        <span className={styles.pill}>{agent.outputs[0]}</span>
        {done ? (
          <span className={styles.pill} style={{ color: pulse.success, borderColor: `${pulse.success}66` }}>
            Complete
          </span>
        ) : null}
        {active ? (
          <span className={styles.pill} style={{ color: agent.accent, borderColor: `${agent.accent}66` }}>
            Running
          </span>
        ) : null}
      </div>
      <div className={styles.footerRow}>
        <span className={styles.stepBadge}>STEP · {agent.progressTo}%</span>
        <Button
          appearance="subtle"
          icon={<ArrowRightRegular />}
          iconPosition="after"
          onClick={(e) => {
            e.stopPropagation();
            navigate(agentWorkspacePath(agent.id, runId));
          }}
        >
          Open workspace
        </Button>
      </div>
    </div>
  );
}
