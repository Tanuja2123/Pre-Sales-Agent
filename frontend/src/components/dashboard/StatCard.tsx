import { Body1, Caption1, makeStyles, shorthands, Title2 } from "@fluentui/react-components";
import type { ReactNode } from "react";
import { pulse } from "../../theme/pulseColors";

const useStyles = makeStyles({
  card: {
    position: "relative",
    ...shorthands.padding("18px", "20px", "16px"),
    borderRadius: "14px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    minHeight: "118px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    transition: "transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease",
    overflow: "hidden",
    boxShadow: pulse.shadowSoft,
    ":hover": {
      transform: "translateY(-1px)",
      borderTopColor: pulse.panelBorderStrong,
      borderRightColor: pulse.panelBorderStrong,
      borderBottomColor: pulse.panelBorderStrong,
      borderLeftColor: pulse.panelBorderStrong,
      boxShadow: pulse.shadowLift,
    },
  },
  accentStripe: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: "3px",
    opacity: 0.85,
  },
  top: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "12px",
  },
  label: {
    display: "block",
    color: pulse.textDim,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    fontSize: "10.5px",
    fontWeight: 700,
  },
  value: {
    display: "block",
    color: pulse.text,
    fontWeight: 700,
    marginTop: "8px",
    lineHeight: 1.05,
    fontSize: "30px",
    letterSpacing: "-0.02em",
    fontVariantNumeric: "tabular-nums",
  },
  sub: {
    display: "block",
    color: pulse.textMuted,
    marginTop: "10px",
    fontSize: "12px",
    lineHeight: 1.4,
  },
  iconWrap: {
    width: "36px",
    height: "36px",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    border: `1px solid ${pulse.panelBorder}`,
  },
});

type StatCardProps = {
  label: string;
  value: string | number;
  sub?: string;
  icon?: ReactNode;
  accent?: string;
};

export function StatCard({ label, value, sub, icon, accent = pulse.teal }: StatCardProps) {
  const styles = useStyles();
  return (
    <div className={styles.card}>
      <div
        className={styles.accentStripe}
        style={{ background: `linear-gradient(90deg, ${accent} 0%, ${accent}44 100%)` }}
      />
      <div className={styles.top}>
        <div>
          <Caption1 className={styles.label}>{label}</Caption1>
          <Title2 className={styles.value}>{value}</Title2>
        </div>
        {icon ? (
          <div
            className={styles.iconWrap}
            style={{ backgroundColor: `${accent}1f`, color: accent, borderColor: `${accent}40` }}
          >
            {icon}
          </div>
        ) : null}
      </div>
      {sub ? <Body1 className={styles.sub}>{sub}</Body1> : null}
    </div>
  );
}
