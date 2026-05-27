import { Body1, Caption1, makeStyles, shorthands, Title1 } from "@fluentui/react-components";
import { Outlet } from "react-router-dom";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  root: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    padding: "24px",
    backgroundColor: pulse.bg,
    backgroundImage: `radial-gradient(900px 420px at 0% 0%, ${pulse.tealGlow}, transparent 65%), radial-gradient(700px 360px at 100% 100%, rgba(99,102,241,0.10), transparent 60%)`,
  },
  card: {
    width: "100%",
    maxWidth: "460px",
    ...shorthands.padding("28px", "28px", "24px"),
    borderRadius: "16px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    boxShadow: pulse.shadowLift,
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "20px",
  },
  brandBar: {
    width: "8px",
    height: "36px",
    borderRadius: "4px",
    background: `linear-gradient(180deg, ${pulse.tealBright}, ${pulse.teal})`,
  },
  title: {
    margin: 0,
    color: pulse.text,
    fontSize: "24px",
    fontWeight: 700,
    letterSpacing: "-0.02em",
  },
  subtitle: {
    color: pulse.textMuted,
    marginTop: "4px",
    display: "block",
  },
});

export function AuthLayout() {
  const styles = useStyles();
  return (
    <div className={styles.root}>
      <div className={styles.card}>
        <div className={styles.brand}>
          <span className={styles.brandBar} aria-hidden />
          <div>
            <Title1 className={styles.title}>Pre-Sales Agent</Title1>
            <Caption1 className={styles.subtitle}>Secure enterprise RFP workspace</Caption1>
          </div>
        </div>
        <Outlet />
      </div>
      <Body1 style={{ position: "absolute", bottom: 16, color: pulse.textDim, fontSize: 12 }}>
        Timeline emails and deadline reminders are sent to your registered address.
      </Body1>
    </div>
  );
}
