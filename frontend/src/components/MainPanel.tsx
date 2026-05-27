import { Caption1, makeStyles, shorthands, Title3 } from "@fluentui/react-components";
import type { ReactNode } from "react";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
    height: "100vh",
    backgroundColor: "transparent",
    color: pulse.text,
    fontFamily: pulse.fontSans,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "20px",
    ...shorthands.padding("18px", "28px", "18px"),
    borderBottom: `1px solid ${pulse.panelBorder}`,
    backgroundColor: "rgba(15, 23, 42, 0.7)",
    backdropFilter: "saturate(140%) blur(8px)",
    WebkitBackdropFilter: "saturate(140%) blur(8px)",
    flexShrink: 0,
  },
  titleWrap: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    minWidth: 0,
  },
  titleBadge: {
    width: "8px",
    height: "32px",
    borderRadius: "4px",
    background: `linear-gradient(180deg, ${pulse.tealBright} 0%, ${pulse.teal} 100%)`,
    boxShadow: `0 0 12px ${pulse.tealGlow}`,
    flexShrink: 0,
  },
  titleText: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  title: {
    margin: 0,
    color: pulse.text,
    fontWeight: 600,
    fontSize: "20px",
    lineHeight: 1.2,
    letterSpacing: "-0.01em",
  },
  subtitle: {
    color: pulse.textMuted,
    marginTop: "2px",
    display: "block",
    maxWidth: "640px",
    lineHeight: 1.45,
    fontSize: "12.5px",
  },
  sessionBadge: {
    fontFamily: pulse.fontMono,
    fontSize: "11px",
    color: pulse.textMuted,
    ...shorthands.padding("6px", "10px"),
    borderRadius: "999px",
    backgroundColor: pulse.panel,
    border: `1px solid ${pulse.panelBorder}`,
    whiteSpace: "nowrap",
    flexShrink: 0,
    letterSpacing: "0.04em",
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    flexWrap: "wrap",
    flexShrink: 0,
  },
  body: {
    flex: 1,
    minHeight: 0,
    overflowY: "auto",
    ...shorthands.padding("20px", "28px", "28px"),
    display: "flex",
    flexDirection: "column",
  },
  chatFeed: {
    flex: 1,
    minHeight: 0,
    overflowY: "auto",
    ...shorthands.padding("24px", "32px"),
    display: "flex",
    flexDirection: "column",
  },
  inputBar: {
    flexShrink: 0,
    ...shorthands.padding("16px", "32px", "22px"),
    borderTop: `1px solid ${pulse.panelBorder}`,
    backgroundColor: "rgba(15, 23, 42, 0.7)",
    backdropFilter: "saturate(140%) blur(8px)",
    WebkitBackdropFilter: "saturate(140%) blur(8px)",
  },
  inputWrap: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    maxWidth: "900px",
    marginLeft: "auto",
    marginRight: "auto",
    width: "100%",
  },
  fauxInput: {
    flex: 1,
    ...shorthands.padding("14px", "18px"),
    borderRadius: "12px",
    backgroundColor: pulse.inputBg,
    border: `1px solid ${pulse.panelBorder}`,
    color: pulse.textDim,
    fontSize: "14px",
  },
});

type MainPanelProps = {
  title: string;
  subtitle?: string;
  sessionId?: string;
  actions?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  variant?: "default" | "chat";
};

export function MainPanel({
  title,
  subtitle,
  sessionId,
  actions,
  children,
  footer,
  variant = "default",
}: MainPanelProps) {
  const styles = useStyles();

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <div className={styles.titleWrap}>
          <span className={styles.titleBadge} aria-hidden />
          <div className={styles.titleText}>
            <Title3 className={styles.title}>{title}</Title3>
            {subtitle ? <Caption1 className={styles.subtitle}>{subtitle}</Caption1> : null}
          </div>
        </div>
        {(actions || sessionId) ? (
          <div className={styles.headerRight}>
            {actions}
            {sessionId ? (
              <span className={styles.sessionBadge}>RUN · {sessionId.slice(0, 8)}</span>
            ) : null}
          </div>
        ) : null}
      </header>
      <div className={variant === "chat" ? styles.chatFeed : styles.body}>{children}</div>
      {footer ? <div className={styles.inputBar}>{footer}</div> : null}
    </main>
  );
}

export function FauxChatInput({ placeholder }: { placeholder: string }) {
  const styles = useStyles();
  return (
    <div className={styles.inputWrap}>
      <div className={styles.fauxInput} aria-hidden>
        {placeholder}
      </div>
    </div>
  );
}
