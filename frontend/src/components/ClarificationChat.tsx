import {
  Avatar,
  Body1,
  Button,
  Caption1,
  Divider,
  makeStyles,
  mergeClasses,
  shorthands,
  Spinner,
  Subtitle2,
  Text,
  Textarea,
  tokens,
} from "@fluentui/react-components";
import {
  BotRegular,
  DocumentTextRegular,
  LightbulbRegular,
  SendFilled,
  SparkleRegular,
} from "@fluentui/react-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { getRunChat, postRunChat, type ChatMessage } from "../api/client";

const useStyles = makeStyles({
  root: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: tokens.spacingHorizontalM,
    flexWrap: "wrap",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
  },
  headerText: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXXS,
    minWidth: 0,
  },
  headerTitle: {
    display: "block",
    lineHeight: tokens.lineHeightBase400,
  },
  headerSubtitle: {
    display: "block",
    color: tokens.colorNeutralForeground3,
    lineHeight: tokens.lineHeightBase200,
  },
  thread: {
    minHeight: "320px",
    maxHeight: "520px",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalL,
    ...shorthands.padding(tokens.spacingVerticalL, tokens.spacingHorizontalL),
    borderRadius: tokens.borderRadiusXLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground2,
  },
  row: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "flex-start",
  },
  rowUser: {
    flexDirection: "row-reverse",
  },
  bubble: {
    maxWidth: "78%",
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXXS,
    ...shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalL),
    borderRadius: tokens.borderRadiusLarge,
    boxShadow: tokens.shadow2,
  },
  bubbleUser: {
    backgroundColor: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
    borderBottomRightRadius: tokens.borderRadiusSmall,
  },
  bubbleAssistant: {
    backgroundColor: tokens.colorNeutralBackground1,
    color: tokens.colorNeutralForeground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderBottomLeftRadius: tokens.borderRadiusSmall,
  },
  bubbleRole: {
    display: "block",
    opacity: 0.8,
    fontWeight: tokens.fontWeightSemibold,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    fontSize: tokens.fontSizeBase100,
  },
  bubbleText: {
    display: "block",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    lineHeight: tokens.lineHeightBase400,
    fontSize: tokens.fontSizeBase300,
  },
  bubbleMeta: {
    fontSize: tokens.fontSizeBase100,
    opacity: 0.6,
    marginTop: tokens.spacingVerticalXXS,
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacingVerticalM,
    color: tokens.colorNeutralForeground3,
    paddingTop: tokens.spacingVerticalXXL,
    paddingBottom: tokens.spacingVerticalXXL,
  },
  suggestions: {
    display: "flex",
    flexWrap: "wrap",
    gap: tokens.spacingHorizontalXS,
  },
  suggestionsBox: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    ...shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalL),
    borderRadius: tokens.borderRadiusLarge,
    backgroundColor: tokens.colorNeutralBackground3,
    border: `1px dashed ${tokens.colorNeutralStroke2}`,
  },
  suggestionLabel: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    color: tokens.colorNeutralForeground2,
    fontWeight: tokens.fontWeightSemibold,
  },
  compose: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    alignItems: "flex-end",
    ...shorthands.padding(tokens.spacingVerticalM),
    borderRadius: tokens.borderRadiusLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
  },
  input: {
    flex: 1,
  },
  typing: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    alignItems: "center",
    color: tokens.colorNeutralForeground3,
    paddingLeft: tokens.spacingHorizontalM,
  },
  avatarBox: {
    flexShrink: 0,
  },
});

type Props = {
  runId: string;
  initialSuggestions?: string[];
};

const QUICK_PROMPTS = [
  "Add authentication requirements",
  "Explain the proposed architecture",
  "Estimate timeline",
  "Generate tech stack recommendation",
  "Create API flow",
  "Generate user stories",
];

function formatTime(iso?: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function ClarificationChat({ runId, initialSuggestions = [] }: Props) {
  const styles = useStyles();
  const qc = useQueryClient();
  const [draft, setDraft] = useState("");
  const [liveSuggestions, setLiveSuggestions] = useState<string[]>([]);
  const threadRef = useRef<HTMLDivElement>(null);

  const chatQ = useQuery({
    queryKey: ["chat", runId],
    queryFn: () => getRunChat(runId),
    refetchOnWindowFocus: false,
  });

  const sendM = useMutation({
    mutationFn: (message: string) => postRunChat(runId, message),
    onSuccess: (resp) => {
      setDraft("");
      setLiveSuggestions(resp.suggested_questions ?? []);
      void qc.invalidateQueries({ queryKey: ["chat", runId] });
      if (resp.scope_updated) {
        void qc.invalidateQueries({ queryKey: ["output", runId] });
      }
    },
  });

  const messages: ChatMessage[] = chatQ.data?.messages ?? [];

  const suggestions = useMemo(() => {
    const dedup = new Set<string>();
    const merged: string[] = [];
    for (const s of [...liveSuggestions, ...initialSuggestions]) {
      const t = s?.trim();
      if (t && !dedup.has(t.toLowerCase())) {
        dedup.add(t.toLowerCase());
        merged.push(t);
      }
    }
    return merged.slice(0, 8);
  }, [liveSuggestions, initialSuggestions]);

  useEffect(() => {
    const el = threadRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, sendM.isPending]);

  function send(text: string) {
    const t = text.trim();
    if (!t || sendM.isPending) return;
    sendM.mutate(t);
  }

  return (
    <div className={styles.root} role="region" aria-label="Clarification chat">
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Avatar
            icon={<SparkleRegular />}
            color="brand"
            size={36}
            aria-label="Presales agent"
          />
          <div className={styles.headerText}>
            <Subtitle2 as="h2" className={styles.headerTitle}>
              Presales clarification chat
            </Subtitle2>
            <Caption1 as="p" className={styles.headerSubtitle}>
              Refine scope, ask follow-up questions, or request changes — the agent keeps run context.
            </Caption1>
          </div>
        </div>
      </div>

      <div className={styles.thread} ref={threadRef}>
        {chatQ.isLoading ? <Spinner label="Loading conversation…" /> : null}

        {messages.length === 0 && !chatQ.isLoading ? (
          <div className={styles.empty}>
            <SparkleRegular fontSize={36} />
            <Text>The agent will open the conversation once the pipeline completes.</Text>
          </div>
        ) : null}

        {messages.map((m, i) => {
          const isUser = m.role === "user";
          return (
            <div
              key={`${m.timestamp ?? i}-${m.role}`}
              className={mergeClasses(styles.row, isUser ? styles.rowUser : undefined)}
            >
              <div className={styles.avatarBox}>
                <Avatar
                  icon={isUser ? <DocumentTextRegular /> : <BotRegular />}
                  color={isUser ? "colorful" : "brand"}
                  size={32}
                  aria-label={isUser ? "RFP document" : "Presales agent"}
                />
              </div>
              <div
                className={mergeClasses(
                  styles.bubble,
                  isUser ? styles.bubbleUser : styles.bubbleAssistant,
                )}
              >
                <Caption1 as="span" className={styles.bubbleRole}>
                  {isUser ? "RFP document says" : "Presales agent"}
                </Caption1>
                <Body1 as="span" className={styles.bubbleText}>
                  {m.content}
                </Body1>
                {m.timestamp ? (
                  <Caption1 as="span" className={styles.bubbleMeta}>
                    {formatTime(m.timestamp)}
                  </Caption1>
                ) : null}
              </div>
            </div>
          );
        })}

        {sendM.isPending ? (
          <div className={styles.typing}>
            <Spinner size="tiny" />
            <Caption1>Agent is thinking…</Caption1>
          </div>
        ) : null}
      </div>

      <div className={styles.suggestions}>
        {QUICK_PROMPTS.map((p) => (
          <Button
            key={p}
            size="small"
            appearance="subtle"
            disabled={sendM.isPending}
            onClick={() => send(p)}
          >
            {p}
          </Button>
        ))}
      </div>

      <div className={styles.compose}>
        <Textarea
          className={styles.input}
          placeholder="Tell the agent what the RFP requires — data points, clarifying answers, or missing details it needs to know…"
          value={draft}
          onChange={(_, d) => setDraft(d.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && draft.trim()) {
              e.preventDefault();
              send(draft);
            }
          }}
          disabled={sendM.isPending}
          resize="vertical"
          rows={2}
        />
        <Button
          appearance="primary"
          icon={<SendFilled />}
          disabled={!draft.trim() || sendM.isPending}
          onClick={() => send(draft)}
        >
          Send
        </Button>
      </div>

      {suggestions.length > 0 ? (
        <>
          <Divider />
          <div className={styles.suggestionsBox}>
            <Caption1 className={styles.suggestionLabel}>
              <LightbulbRegular /> Suggested questions you may want to answer
            </Caption1>
            <div className={styles.suggestions}>
              {suggestions.map((s) => (
                <Button
                  key={s}
                  size="small"
                  appearance="secondary"
                  disabled={sendM.isPending}
                  onClick={() => send(s)}
                >
                  {s}
                </Button>
              ))}
            </div>
          </div>
        </>
      ) : null}

      {sendM.isError ? (
        <Text style={{ color: tokens.colorPaletteRedForeground1 }}>
          {sendM.error instanceof Error ? sendM.error.message : "Send failed"}
        </Text>
      ) : null}
    </div>
  );
}
