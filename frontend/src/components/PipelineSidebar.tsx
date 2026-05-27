import {
  Body1,
  Button,
  Caption1,
  ProgressBar,
  makeStyles,
  mergeClasses,
  shorthands,
  Text,
} from "@fluentui/react-components";
import {
  AddRegular,
  AppsRegular,
  BoardRegular,
  CheckmarkCircleFilled,
  CircleRegular,
  DocumentDataRegular,
  HistoryRegular,
  HomeRegular,
} from "@fluentui/react-icons";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useState, type ReactElement } from "react";
import { useDropzone } from "react-dropzone";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { analyzeRfp, getApiErrorMessage, getRunStatus } from "../api/client";
import { AGENTS, agentWorkspacePath } from "../config/agents";
import { useAuthStore } from "../stores/authStore";
import { PIPELINE_STAGES, pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  sidebar: {
    width: "300px",
    minWidth: "300px",
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    backgroundColor: pulse.sidebar,
    borderRight: `1px solid ${pulse.sidebarBorder}`,
    color: pulse.text,
    fontFamily: pulse.fontSans,
    flexShrink: 0,
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    ...shorthands.padding("14px", "14px", "12px"),
    borderBottom: `1px solid ${pulse.sidebarBorder}`,
    cursor: "pointer",
    textDecoration: "none",
    color: "inherit",
  },
  logo: {
    width: "36px",
    height: "36px",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: `linear-gradient(135deg, ${pulse.tealDim} 0%, ${pulse.teal} 100%)`,
    color: pulse.bg,
    boxShadow: `0 0 20px ${pulse.tealGlow}`,
  },
  brandName: {
    fontSize: "15px",
    fontWeight: 700,
    letterSpacing: "0.12em",
    color: pulse.text,
  },
  brandTag: {
    fontSize: "10px",
    color: pulse.teal,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    ...shorthands.padding("10px", "10px", "8px"),
    borderBottom: `1px solid ${pulse.sidebarBorder}`,
  },
  navSection: {
    display: "block",
    fontSize: "10px",
    color: pulse.textDim,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    ...shorthands.padding("10px", "10px", "6px"),
  },
  session: {
    ...shorthands.padding("10px", "14px"),
    borderBottom: `1px solid ${pulse.sidebarBorder}`,
  },
  sessionLabel: {
    fontSize: "11px",
    color: pulse.textDim,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: "6px",
  },
  sessionId: {
    fontFamily: pulse.fontMono,
    fontSize: "11px",
    color: pulse.textMuted,
    wordBreak: "break-all",
  },
  progressBlock: {
    ...shorthands.padding("12px", "14px"),
    borderBottom: `1px solid ${pulse.sidebarBorder}`,
  },
  progressLabel: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
  },
  checklist: {
    flex: 1,
    overflowY: "auto",
    ...shorthands.padding("6px", "8px"),
  },
  checkItem: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    ...shorthands.padding("9px", "10px"),
    borderRadius: "8px",
    fontSize: "13px",
    color: pulse.textMuted,
    textDecoration: "none",
    transition: "background 0.15s ease, color 0.15s ease",
    ":hover": {
      backgroundColor: pulse.tealGlow,
      color: pulse.text,
    },
  },
  checkItemActive: {
    backgroundColor: pulse.tealGlow,
    color: pulse.tealBright,
  },
  checkItemDone: {
    color: pulse.text,
  },
  dotDone: {
    color: pulse.success,
    fontSize: "16px",
    flexShrink: 0,
  },
  dotPending: {
    color: pulse.textDim,
    fontSize: "14px",
    flexShrink: 0,
  },
  uploadBlock: {
    ...shorthands.padding("10px", "14px", "12px"),
    borderTop: `1px solid ${pulse.sidebarBorder}`,
  },
  dropzone: {
    borderRadius: "10px",
    ...shorthands.border("1px", "dashed", pulse.panelBorder),
    ...shorthands.padding("12px", "10px"),
    textAlign: "center",
    cursor: "pointer",
    backgroundColor: pulse.panel,
    transition: "border-color 0.2s, background 0.2s",
    ":hover": {
      borderTopColor: pulse.teal,
      borderRightColor: pulse.teal,
      borderBottomColor: pulse.teal,
      borderLeftColor: pulse.teal,
      backgroundColor: pulse.tealGlow,
    },
  },
  dropzoneActive: {
    ...shorthands.border("1px", "dashed", pulse.teal),
    backgroundColor: pulse.tealGlow,
  },
  footer: {
    ...shorthands.padding("10px", "16px"),
    borderTop: `1px solid ${pulse.sidebarBorder}`,
    fontSize: "11px",
    color: pulse.textDim,
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  safetyDot: {
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    backgroundColor: pulse.success,
    boxShadow: `0 0 6px ${pulse.success}`,
  },
  uploadError: {
    marginTop: "8px",
    fontSize: "11px",
    lineHeight: "1.4",
    color: pulse.danger,
  },
  uploadSuccess: {
    marginTop: "8px",
    fontSize: "11px",
    lineHeight: "1.4",
    color: pulse.success,
  },
  userBlock: {
    ...shorthands.padding("10px", "14px"),
    borderBottom: `1px solid ${pulse.sidebarBorder}`,
  },
  userEmail: {
    fontSize: "12px",
    color: pulse.textMuted,
    wordBreak: "break-all",
  },
});


export function PipelineSidebar() {
  const styles = useStyles();
  const navigate = useNavigate();
  const location = useLocation();
  const { runId } = useParams();
  const path = location.pathname;
  const isIntake = path === "/intake";
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const statusQ = useQuery({
    queryKey: ["status", runId],
    queryFn: () => getRunStatus(runId!),
    enabled: Boolean(runId) && (path.includes("/analysis") || path.includes("/results") || path.includes("/run/")),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      if (s === "complete" || s === "failed" || s === "aborted") return false;
      return 500;
    },
  });

  const progress = path.startsWith("/results") ? 100 : (statusQ.data?.progress ?? 0);
  const status = statusQ.data?.status ?? "";
  const showProgress =
    Boolean(runId) &&
    (path.startsWith("/analysis") || path.startsWith("/results") || path.includes("/run/"));

  const onDrop = useCallback(
    async (files: File[]) => {
      const f = files[0];
      if (!f) return;
      setUploadError(null);
      setUploadNotice(null);
      setUploading(true);
      try {
        const { run_id, message } = await analyzeRfp(f);
        if (message) setUploadNotice(message);
        navigate(`/analysis/${run_id}`);
      } catch (err) {
        setUploadError(getApiErrorMessage(err));
      } finally {
        setUploading(false);
      }
    },
    [navigate],
  );

  const { getRootProps, getInputProps, isDragActive, isDragAccept } = useDropzone({
    onDrop: (files) => void onDrop(files),
    multiple: false,
    disabled: !isIntake || uploading,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
  });

  const navBtn = (to: string, label: string, icon: ReactElement, match: boolean) => (
    <Button
      appearance={match ? "primary" : "subtle"}
      icon={icon}
      onClick={() => navigate(to)}
      style={{ justifyContent: "flex-start", width: "100%" }}
    >
      {label}
    </Button>
  );

  return (
    <aside className={styles.sidebar}>
      <Link to="/dashboard" className={styles.brand}>
        <div className={styles.logo}>
          <DocumentDataRegular fontSize={20} />
        </div>
        <div>
          <div className={styles.brandName}>PRESALES</div>
          <div className={styles.brandTag}>AI command center</div>
        </div>
      </Link>

      <nav className={styles.nav} aria-label="Main navigation">
        {navBtn("/dashboard", "Dashboard", <BoardRegular />, path === "/dashboard")}
        {navBtn("/agents", "Agent fleet", <AppsRegular />, path.startsWith("/agents") && !runId)}
        {navBtn("/intake", "New intake", <HomeRegular />, path === "/intake")}
        {navBtn("/history", "Run history", <HistoryRegular />, path.startsWith("/history"))}
      </nav>

      {user ? (
        <div className={styles.userBlock}>
          <div className={styles.sessionLabel}>Signed in</div>
          <Text className={styles.userEmail}>{user.full_name}</Text>
          <Caption1 className={styles.userEmail}>{user.email}</Caption1>
          <Button
            size="small"
            appearance="subtle"
            style={{ marginTop: 8, width: "100%" }}
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </Button>
        </div>
      ) : null}

      {runId ? (
        <div className={styles.session}>
          <div className={styles.sessionLabel}>Active run</div>
          <Text className={styles.sessionId}>{runId}</Text>
          <Button
            size="small"
            appearance="subtle"
            style={{ marginTop: 8, width: "100%" }}
            onClick={() => navigate(`/run/${runId}/agents`)}
          >
            All agent workspaces
          </Button>
        </div>
      ) : (
        <div className={styles.session}>
          <div className={styles.sessionLabel}>Session</div>
          <Text className={styles.sessionId}>— no active run —</Text>
        </div>
      )}

      {showProgress ? (
        <div className={styles.progressBlock}>
          <div className={styles.progressLabel}>
            <Caption1 style={{ color: pulse.textMuted, fontSize: "11px" }}>Pipeline</Caption1>
            <Caption1 style={{ color: pulse.teal, fontWeight: 600 }}>{Math.round(progress)}%</Caption1>
          </div>
          <ProgressBar value={progress / 100} max={1} thickness="medium" color="brand" />
          {status ? (
            <Caption1 style={{ color: pulse.textDim, marginTop: 8, fontSize: "11px" }}>
              {status}
            </Caption1>
          ) : null}
        </div>
      ) : null}

      <div className={styles.checklist} role="list" aria-label="Pipeline stages">
        <Caption1 className={styles.navSection}>Agents</Caption1>
        {AGENTS.map((agent, index) => {
          const stage = PIPELINE_STAGES[index];
          if (!stage) return null;
          const prevTo = index > 0 ? PIPELINE_STAGES[index - 1].to : 0;
          const done = progress >= stage.to;
          const active = progress >= prevTo && progress < stage.to;
          const href = runId ? agentWorkspacePath(agent.id, runId) : `/agents/${agent.id}`;
          const isCurrent = path.endsWith(`/agents/${agent.id}`) || path.endsWith(`/${agent.id}`);
          return (
            <Link
              key={agent.id}
              to={href}
              className={mergeClasses(
                styles.checkItem,
                done && styles.checkItemDone,
                (active || isCurrent) && styles.checkItemActive,
              )}
              role="listitem"
            >
              {done ? (
                <CheckmarkCircleFilled className={styles.dotDone} />
              ) : (
                <CircleRegular className={styles.dotPending} />
              )}
              <span>{agent.shortName}</span>
            </Link>
          );
        })}
      </div>

      {isIntake ? (
        <div className={styles.uploadBlock}>
          <Caption1 style={{ color: pulse.textDim, display: "block", marginBottom: 8, fontSize: "11px" }}>
            Documents
          </Caption1>
          <div
            {...getRootProps()}
            className={mergeClasses(styles.dropzone, (isDragActive || isDragAccept) && styles.dropzoneActive)}
          >
            <input {...getInputProps()} />
            <AddRegular style={{ color: pulse.teal, fontSize: 20, marginBottom: 6 }} />
            <Body1 style={{ fontSize: "13px", color: pulse.text, margin: 0 }}>
              {uploading ? "Uploading…" : "Upload RFP"}
            </Body1>
            <Caption1 style={{ color: pulse.textDim, fontSize: "11px", marginTop: 4 }}>
              Supported: .pdf · .docx · .txt
            </Caption1>
          </div>
          {uploadNotice ? (
            <Text className={styles.uploadSuccess} role="status">
              {uploadNotice}
            </Text>
          ) : null}
          {uploadError ? (
            <Text className={styles.uploadError} role="alert">
              {uploadError}
            </Text>
          ) : null}
        </div>
      ) : null}

      <div className={styles.footer}>
        <span className={styles.safetyDot} aria-hidden />
        Groq · multi-agent pipeline
      </div>
    </aside>
  );
}
