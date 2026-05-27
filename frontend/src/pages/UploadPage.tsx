import { Caption1, makeStyles, shorthands, Subtitle2 } from "@fluentui/react-components";
import { ChatBubble } from "../components/ChatBubble";
import { FauxChatInput, MainPanel } from "../components/MainPanel";
import { SurfaceCard } from "../components/ui/SurfaceCard";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  hint: {
    color: pulse.textDim,
    fontSize: "13px",
    marginTop: "24px",
    ...shorthands.padding("12px", "16px"),
    borderRadius: "10px",
    backgroundColor: pulse.panelElevated,
    border: `1px solid ${pulse.panelBorder}`,
    maxWidth: "520px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: "14px",
    marginTop: "18px",
    maxWidth: "820px",
    "@media (min-width: 920px)": {
      gridTemplateColumns: "1fr 1fr 1fr",
    },
  },
  stepTitle: {
    display: "block",
    color: pulse.text,
    marginBottom: "6px",
  },
  stepText: {
    color: pulse.textMuted,
    lineHeight: 1.5,
  },
});

export function UploadPage() {
  const styles = useStyles();

  return (
    <MainPanel
      title="Pre-Sales Intake"
      subtitle="Upload an RFP in the sidebar — then track each agent on its own workspace from the dashboard."
      variant="chat"
      footer={<FauxChatInput placeholder="Upload a file from the sidebar to begin…" />}
    >
      <ChatBubble role="bot">
        Welcome. Drop a PDF, Word document, or plain-text RFP in the <strong>Documents</strong> panel on the left.
        I'll extract requirements, build a summary, surface clarifying questions, and draft a full proposal with Groq.
      </ChatBubble>
      <ChatBubble role="bot">
        Tip: try <code style={{ color: pulse.teal }}>samples/sample-rfp-it-services.txt</code> from the repo for a
        quick test. Set <code style={{ color: pulse.teal }}>GROQ_API_KEY</code> in <code style={{ color: pulse.teal }}>.env</code> for fast cloud inference.
      </ChatBubble>
      <ChatBubble role="user" avatarLabel="You">
        Ready when you are — I'll upload from the sidebar.
      </ChatBubble>
      <div className={styles.grid}>
        <SurfaceCard compact>
          <Subtitle2 className={styles.stepTitle}>1. Upload</Subtitle2>
          <Caption1 className={styles.stepText}>Use the Documents area in the sidebar for the RFP source file.</Caption1>
        </SurfaceCard>
        <SurfaceCard compact>
          <Subtitle2 className={styles.stepTitle}>2. Analyze</Subtitle2>
          <Caption1 className={styles.stepText}>Agents extract requirements, timeline, risks, and clarifying questions.</Caption1>
        </SurfaceCard>
        <SurfaceCard compact>
          <Subtitle2 className={styles.stepTitle}>3. Finalize</Subtitle2>
          <Caption1 className={styles.stepText}>Answer questions and generate the final enterprise proposal draft.</Caption1>
        </SurfaceCard>
      </div>
      <div className={styles.hint}>
        <Caption1>
          Supported: PDF · DOCX · TXT · Pipeline stages appear in the left checklist as your run progresses.
        </Caption1>
      </div>
    </MainPanel>
  );
}
