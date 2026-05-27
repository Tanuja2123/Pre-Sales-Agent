import { Caption1, makeStyles, shorthands } from "@fluentui/react-components";
import { AGENTS } from "../../config/agents";
import { pulse } from "../../theme/pulseColors";

const useStyles = makeStyles({
  wrap: {
    ...shorthands.padding("22px", "24px"),
    borderRadius: "14px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    boxShadow: pulse.shadowSoft,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "16px",
    gap: "12px",
    flexWrap: "wrap",
  },
  label: {
    color: pulse.textDim,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    fontSize: "10.5px",
    fontWeight: 700,
    display: "block",
  },
  progressMeta: {
    fontFamily: pulse.fontMono,
    color: pulse.textMuted,
    fontSize: "12px",
  },
  track: {
    position: "relative",
    width: "100%",
    height: "3px",
    backgroundColor: pulse.panelBorder,
    borderRadius: "999px",
    margin: "18px 0 22px",
  },
  trackFill: {
    position: "absolute",
    top: 0,
    left: 0,
    bottom: 0,
    borderRadius: "999px",
    background: `linear-gradient(90deg, ${pulse.tealBright} 0%, ${pulse.teal} 60%, ${pulse.accentBlue} 100%)`,
    boxShadow: `0 0 12px ${pulse.tealGlow}`,
    transition: "width 0.35s ease",
  },
  row: {
    display: "grid",
    gridTemplateColumns: `repeat(${AGENTS.length}, minmax(0, 1fr))`,
    gap: "10px",
  },
  node: {
    position: "relative",
    ...shorthands.padding("12px", "12px"),
    borderRadius: "12px",
    border: `1px solid ${pulse.panelBorder}`,
    backgroundColor: pulse.panel,
    textAlign: "left",
    minWidth: 0,
    display: "flex",
    alignItems: "center",
    gap: "10px",
    transition: "border-color 0.2s, box-shadow 0.2s, background-color 0.2s",
  },
  bullet: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    flexShrink: 0,
    backgroundColor: pulse.panelBorderStrong,
    boxShadow: "inset 0 0 0 2px rgba(255,255,255,0.04)",
  },
  textCol: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  nodeTitle: {
    fontSize: "12.5px",
    fontWeight: 600,
    color: pulse.text,
    display: "block",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    letterSpacing: "-0.005em",
  },
  nodeSub: {
    fontSize: "10.5px",
    color: pulse.textDim,
    marginTop: "2px",
    display: "block",
    fontFamily: pulse.fontMono,
  },
});

type PipelineFlowProps = {
  activeAgentId?: string;
  progress?: number;
};

export function PipelineFlow({ activeAgentId, progress = 0 }: PipelineFlowProps) {
  const styles = useStyles();
  const safeProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <Caption1 className={styles.label}>Multi-agent orchestration</Caption1>
        <span className={styles.progressMeta}>{Math.round(safeProgress)}% complete</span>
      </div>
      <div className={styles.track} aria-hidden>
        <div className={styles.trackFill} style={{ width: `${safeProgress}%` }} />
      </div>
      <div className={styles.row}>
        {AGENTS.map((agent, i) => {
          const prevTo = i > 0 ? AGENTS[i - 1].progressTo : 0;
          const done = progress >= agent.progressTo;
          const active =
            activeAgentId === agent.id || (progress >= prevTo && progress < agent.progressTo);
          const bulletColor = done
            ? agent.accent
            : active
              ? agent.accent
              : pulse.panelBorderStrong;
          return (
            <div
              key={agent.id}
              className={styles.node}
              style={{
                borderColor: active ? agent.accent : done ? `${agent.accent}66` : undefined,
                boxShadow: active ? `0 0 0 1px ${agent.accent}55, 0 0 18px ${agent.accent}22` : undefined,
                backgroundColor: active ? `${agent.accent}0d` : undefined,
              }}
              title={agent.shortName}
            >
              <span
                className={styles.bullet}
                style={{
                  backgroundColor: bulletColor,
                  boxShadow: active ? `0 0 0 4px ${agent.accent}22` : undefined,
                }}
                aria-hidden
              />
              <div className={styles.textCol}>
                <span className={styles.nodeTitle}>{agent.shortName}</span>
                <span className={styles.nodeSub}>≤ {agent.progressTo}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
