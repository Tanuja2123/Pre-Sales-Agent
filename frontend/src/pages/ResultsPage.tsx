import {
  Badge,
  Body1,
  Button,
  Caption1,
  Card,
  CardHeader,
  Divider,
  makeStyles,
  MessageBar,
  MessageBarBody,
  shorthands,
  Skeleton,
  SkeletonItem,
  Subtitle2,
  Tab,
  TabList,
  TabValue,
  Textarea,
  Text,
  Title2,
  Title3,
  tokens,
} from "@fluentui/react-components";
import {
  BuildingRegular,
  ChatMultipleRegular,
  ClipboardTextLtrRegular,
  CopyRegular,
  DocumentBulletListRegular,
  DocumentDataRegular,
  DocumentEditRegular,
  FlagRegular,
  LightbulbRegular,
  QuestionCircleRegular,
  TargetRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getRunOutput, getApiErrorMessage, isApiNotFound, resolveClarifications } from "../api/client";
import { ClarificationChat } from "../components/ClarificationChat";
import { DraftBody } from "../components/DraftBody";
import { MainPanel } from "../components/MainPanel";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import type {
  PipelineOutput,
  QuestionOut,
  RequirementOut,
  TimelineMilestoneOut,
} from "../types/output";

const useStyles = makeStyles({
  metaBar: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: tokens.spacingHorizontalS,
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    marginBottom: tokens.spacingVerticalM,
    borderRadius: tokens.borderRadiusLarge,
    backgroundColor: tokens.colorNeutralBackground2,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    flexShrink: 0,
  },
  statChips: {
    display: "flex",
    flexWrap: "wrap",
    gap: tokens.spacingHorizontalS,
    alignItems: "center",
    minWidth: 0,
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "auto minmax(0, 1fr)",
    columnGap: tokens.spacingHorizontalM,
    rowGap: tokens.spacingVerticalS,
    marginTop: tokens.spacingVerticalS,
    maxWidth: "min(100%, 720px)",
  },
  metaLabel: {
    color: tokens.colorNeutralForeground3,
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
    whiteSpace: "nowrap",
    paddingTop: "2px",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  metaValue: {
    color: tokens.colorNeutralForeground1,
    fontSize: tokens.fontSizeBase300,
    lineHeight: tokens.lineHeightBase400,
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr)",
    gap: tokens.spacingVerticalM,
    "@media (min-width: 980px)": {
      gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
    },
  },
  summaryCard: {
    position: "relative",
    padding: `${tokens.spacingVerticalL} ${tokens.spacingHorizontalL}`,
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    boxShadow: tokens.shadow2,
  },
  summaryHeader: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    marginBottom: tokens.spacingVerticalS,
  },
  summaryIcon: {
    width: "30px",
    height: "30px",
    borderRadius: tokens.borderRadiusMedium,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.colorBrandBackground2,
    color: tokens.colorBrandForeground1,
    flexShrink: 0,
  },
  summaryEyebrow: {
    color: tokens.colorNeutralForeground3,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontSize: tokens.fontSizeBase200,
    fontWeight: tokens.fontWeightSemibold,
    display: "block",
  },
  summaryTitle: {
    color: tokens.colorNeutralForeground1,
    fontSize: tokens.fontSizeBase400,
    fontWeight: tokens.fontWeightSemibold,
    lineHeight: tokens.lineHeightBase400,
    margin: 0,
  },
  summaryBody: {
    color: tokens.colorNeutralForeground2,
    fontSize: tokens.fontSizeBase300,
    lineHeight: tokens.lineHeightBase400,
    margin: 0,
    whiteSpace: "pre-wrap",
  },
  bulletList: {
    margin: 0,
    paddingLeft: tokens.spacingHorizontalL,
    color: tokens.colorNeutralForeground2,
    display: "grid",
    gap: tokens.spacingVerticalXXS,
  },
  questionCard: {
    position: "relative",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    backgroundColor: tokens.colorNeutralBackground1,
    overflow: "hidden",
    boxShadow: tokens.shadow2,
  },
  questionHeader: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    background: `linear-gradient(180deg, ${tokens.colorNeutralBackground2}, ${tokens.colorNeutralBackground1})`,
  },
  questionMetaRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: tokens.spacingHorizontalS,
    alignItems: "center",
    marginTop: tokens.spacingVerticalXS,
  },
  questionBody: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL} ${tokens.spacingVerticalL}`,
    display: "grid",
    gap: tokens.spacingVerticalS,
  },
  inlineLabel: {
    display: "block",
    color: tokens.colorNeutralForeground3,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    fontSize: tokens.fontSizeBase200,
    fontWeight: tokens.fontWeightSemibold,
  },
  suggestionPill: {
    justifyContent: "flex-start",
    height: "auto",
    textAlign: "left",
    whiteSpace: "normal",
    lineHeight: 1.4,
    paddingTop: "10px",
    paddingBottom: "10px",
  },
  submitCard: {
    marginTop: tokens.spacingVerticalL,
    padding: `${tokens.spacingVerticalL} ${tokens.spacingHorizontalL}`,
    border: `1px solid ${tokens.colorBrandStroke2}`,
    background: `linear-gradient(180deg, ${tokens.colorBrandBackground2} 0%, ${tokens.colorNeutralBackground1} 100%)`,
    borderRadius: tokens.borderRadiusLarge,
    boxShadow: tokens.shadow4,
  },
  section: {
    marginTop: tokens.spacingVerticalM,
  },
  fieldLabel: {
    color: tokens.colorNeutralForeground3,
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    marginTop: tokens.spacingVerticalM,
    marginBottom: tokens.spacingVerticalXXS,
  },
  list: {
    marginTop: tokens.spacingVerticalS,
    paddingLeft: tokens.spacingHorizontalXL,
  },
  draftBody: {
    whiteSpace: "pre-wrap",
    lineHeight: tokens.lineHeightBase300,
    color: tokens.colorNeutralForeground2,
    ...shorthands.margin(0),
  },
  winTheme: {
    ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalM),
    backgroundColor: tokens.colorPaletteMarigoldBackground2,
    borderLeft: `4px solid ${tokens.colorPaletteMarigoldBorder2}`,
    marginTop: tokens.spacingVerticalM,
    borderRadius: tokens.borderRadiusMedium,
  },
  tabSurface: {
    position: "relative",
    display: "flex",
    alignItems: "stretch",
    width: "100%",
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: tokens.borderRadiusLarge,
    ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalM),
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    flexShrink: 0,
  },
  tabContent: {
    flex: 1,
    minHeight: 0,
    marginTop: tokens.spacingVerticalM,
  },
  tabList: {
    display: "flex",
    flexWrap: "wrap",
    width: "100%",
    rowGap: tokens.spacingVerticalS,
    columnGap: tokens.spacingHorizontalM,
  },
  tabLabel: {
    display: "inline-flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    fontWeight: tokens.fontWeightSemibold,
    whiteSpace: "nowrap",
  },
  tabCount: {
    minWidth: "22px",
    height: "22px",
    paddingLeft: "8px",
    paddingRight: "8px",
    borderRadius: "999px",
    fontSize: tokens.fontSizeBase200,
    fontWeight: tokens.fontWeightSemibold,
    lineHeight: 1,
  },
  tableWrap: {
    borderRadius: tokens.borderRadiusLarge,
    overflow: "auto",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    maxWidth: "100%",
  },
  reqTable: {
    tableLayout: "fixed",
    width: "100%",
  },
  reqCellPad: {
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalS,
    paddingRight: tokens.spacingHorizontalS,
  },
  reqColId: {
    width: "7%",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    verticalAlign: "top",
  },
  reqColMaf: {
    width: "5%",
    whiteSpace: "nowrap",
    verticalAlign: "top",
  },
  reqColPriority: {
    width: "8%",
    whiteSpace: "nowrap",
    verticalAlign: "top",
  },
  reqColType: {
    width: "9%",
    verticalAlign: "top",
  },
  reqColSection: {
    width: "10%",
    verticalAlign: "top",
  },
  reqColText: {
    width: "56%",
    verticalAlign: "top",
    wordBreak: "break-word",
  },
  reqColAmb: {
    width: "5%",
    textAlign: "right",
    whiteSpace: "nowrap",
    verticalAlign: "top",
  },
  reqTextBody: {
    display: "block",
    width: "100%",
    maxWidth: "100%",
    wordBreak: "break-word",
    lineHeight: tokens.lineHeightBase500,
  },
  tableRow: {
    transition: "background-color 0.12s ease",
    ":hover": {
      backgroundColor: tokens.colorNeutralBackground2,
    },
  },
  skeletonBlock: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    marginTop: tokens.spacingVerticalL,
    maxWidth: "480px",
  },
  contentGrid: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr)",
    gap: tokens.spacingVerticalL,
    "@media (min-width: 1100px)": {
      gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 0.55fr)",
    },
  },
  compactCard: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    backgroundColor: tokens.colorNeutralBackground1,
  },
  draftShell: {
    maxWidth: "920px",
    marginLeft: "auto",
    marginRight: "auto",
  },
  draftDocument: {
    padding: `${tokens.spacingVerticalXL} ${tokens.spacingHorizontalXXL}`,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusXLarge,
    backgroundColor: tokens.colorNeutralBackground1,
    boxShadow: tokens.shadow4,
  },
  draftToolbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
    flexWrap: "wrap",
    marginBottom: tokens.spacingVerticalM,
  },
});

function SummaryCard({
  eyebrow,
  title,
  body,
  list,
  emptyText,
  icon,
  styles,
}: {
  eyebrow: string;
  title: string;
  body?: string;
  list?: string[];
  emptyText?: string;
  icon: React.ReactNode;
  styles: ReturnType<typeof useStyles>;
}) {
  return (
    <div className={styles.summaryCard}>
      <div className={styles.summaryHeader}>
        <div className={styles.summaryIcon}>{icon}</div>
        <div>
          <Caption1 className={styles.summaryEyebrow}>{eyebrow}</Caption1>
          <Subtitle2 className={styles.summaryTitle}>{title}</Subtitle2>
        </div>
      </div>
      {list ? (
        list.length === 0 ? (
          <Body1 style={{ color: tokens.colorNeutralForeground3 }}>{emptyText ?? "—"}</Body1>
        ) : (
          <ul className={styles.bulletList}>
            {list.map((k, i) => (
              <li key={i}>{k}</li>
            ))}
          </ul>
        )
      ) : (
        <Body1 className={styles.summaryBody}>{body ?? "—"}</Body1>
      )}
    </div>
  );
}

function mafBadge(level?: string) {
  const v = (level ?? "?").toUpperCase();
  const color =
    v === "M" ? "danger" : v === "A" ? "warning" : v === "F" ? "success" : "informative";
  return (
    <Badge appearance="filled" color={color}>
      {v}
    </Badge>
  );
}

function priorityBadge(p?: string) {
  const pLow = (p ?? "").toLowerCase();
  if (pLow === "mandatory") {
    return (
      <Badge appearance="filled" color="danger">
        Mandatory
      </Badge>
    );
  }
  if (pLow === "desirable") {
    return (
      <Badge appearance="tint" color="important">
        Desirable
      </Badge>
    );
  }
  return <Badge appearance="outline">{p ?? "—"}</Badge>;
}

function possibleAnswerSuggestions(qItem: QuestionOut, linkedReq?: RequirementOut): string[] {
  const reqLabel = linkedReq?.requirement_id
    ? `${linkedReq.requirement_id}`
    : qItem.source_requirement || "this requirement";
  const assumption = (qItem.assumption_if_unanswered ?? "").trim();
  const category = (qItem.category ?? "").toLowerCase();

  const suggestions: string[] = [];
  if (assumption) {
    suggestions.push(assumption);
  }

  if (category === "timeline" || category === "submission") {
    suggestions.push(
      `For ${reqLabel}, we confirm milestone owners and strict weekly checkpoints, with escalation within 24 hours for any blocker.`
    );
  } else if (category === "commercial") {
    suggestions.push(
      `For ${reqLabel}, we align commercials to scope baselines, change-control approval, and agreed acceptance criteria before sign-off.`
    );
  } else if (category === "evaluation") {
    suggestions.push(
      `For ${reqLabel}, we will provide measurable acceptance criteria, audit evidence, and periodic review checkpoints.`
    );
  } else {
    suggestions.push(
      `For ${reqLabel}, we confirm scope, owners, constraints, dependencies, and acceptance criteria with client sign-off.`
    );
  }

  suggestions.push(
    `For ${reqLabel}, if client confirmation is delayed, we proceed with the documented assumption and update this item in the first governance meeting.`
  );

  const dedup: string[] = [];
  const seen = new Set<string>();
  for (const s of suggestions) {
    const key = s.trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    dedup.push(s.trim());
  }
  return dedup.slice(0, 3);
}

export function ResultsPage() {
  const styles = useStyles();
  const { runId } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState<TabValue>("summary");
  const [copied, setCopied] = useState(false);
  const [answerByQuestion, setAnswerByQuestion] = useState<Record<string, string>>({});
  const [additionalFiles, setAdditionalFiles] = useState<File[]>([]);
  const q = useQuery({
    queryKey: ["output", runId],
    queryFn: () => getRunOutput(runId!),
    enabled: Boolean(runId),
    retry: (failureCount, error) => {
      if (isApiNotFound(error)) return false;
      return failureCount < 5;
    },
    retryDelay: 400,
    refetchOnWindowFocus: (query) => {
      if (query.state.error && isApiNotFound(query.state.error)) return false;
      return true;
    },
  });

  const data = q.data as PipelineOutput | undefined;
  const runMissing = q.isError && isApiNotFound(q.error);
  const clarificationDocument = data?.clarification_document;

  useEffect(() => {
    if (!copied) return;
    const t = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(t);
  }, [copied]);

  if (!runId) {
    return (
      <MainPanel title="Results" subtitle="Missing run id.">
        <Text>Missing run id.</Text>
      </MainPanel>
    );
  }

  const reqs = (data?.requirements ?? []) as RequirementOut[];
  const questions = (data?.questions ?? []) as QuestionOut[];
  const timeline = (data?.timeline ?? []) as TimelineMilestoneOut[];
  const sections = (data?.draft_response?.sections ?? []).filter(
    (section) => !/strict timeline table/i.test(section.title ?? ""),
  );
  const answeredQuestions = questions.filter((qItem, qi) => {
    const qid = qItem.question_id ?? `q-${qi}`;
    return Boolean((answerByQuestion[qid] ?? "").trim());
  }).length;
  const timelineColumns: DataTableColumn<TimelineMilestoneOut>[] = [
    { key: "project", label: "Project", width: "14%", render: (row) => row.project_name ?? "—" },
    { key: "milestone", label: "Milestone / Task", width: "18%", render: (row) => row.milestone ?? "—" },
    { key: "start", label: "Start", width: "10%", render: (row) => row.start_date ?? "—" },
    { key: "deadline", label: "Deadline", width: "10%", render: (row) => row.end_deadline ?? "—" },
    {
      key: "deliverables",
      label: "Required deliverables",
      width: "24%",
      render: (row) => row.required_deliverables ?? row.dependency ?? "—",
    },
    { key: "status", label: "Status", width: "10%", render: (row) => row.status ?? "—" },
    { key: "priority", label: "Priority", width: "8%", render: (row) => row.priority ?? "—" },
    { key: "sla", label: "Escalation SLA", width: "12%", render: (row) => row.escalation_sla ?? "—" },
  ];
  const requirementColumns: DataTableColumn<RequirementOut>[] = [
    { key: "id", label: "ID", width: "9%", render: (row) => row.requirement_id ?? "—" },
    { key: "maf", label: "MAF", width: "7%", render: (row) => mafBadge(row.maf_classification) },
    { key: "priority", label: "Priority", width: "11%", render: (row) => priorityBadge(row.priority) },
    { key: "type", label: "Type", width: "13%", render: (row) => row.type ?? "—" },
    { key: "section", label: "Section", width: "14%", render: (row) => row.source_section ?? "—" },
    { key: "text", label: "Requirement", width: "38%", render: (row) => <Text className={styles.reqTextBody}>{row.text ?? ""}</Text> },
    { key: "ambiguity", label: "Amb.", width: "8%", render: (row) => row.ambiguity_score ?? "—" },
  ];
  const resolveM = useMutation({
    mutationFn: () =>
      resolveClarifications(
        runId!,
        {
          answers: answerByQuestion,
          suggested_inputs: Object.fromEntries(
            questions.map((qItem, qi) => [
              qItem.question_id ?? `q-${qi}`,
              qItem.assumption_if_unanswered
                ? `Possible answer baseline: ${qItem.assumption_if_unanswered}`
                : "Possible answer baseline: confirm scope, owner, constraints, and dates.",
            ]),
          ),
          additional_notes: "",
        },
        additionalFiles,
      ),
    onSuccess: () => {
      void q.refetch();
      setTab("draft");
    },
  });

  async function copyDraft() {
    const text = sections.map((section) => `${section.title ?? ""}\n\n${section.body ?? ""}`).join("\n\n");
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      /* ignore */
    }
  }

  return (
    <MainPanel
      title="Pipeline results"
      subtitle={data?.rfp?.filename ? `RFP: ${data.rfp.filename}` : "Structured outputs from the agent pipeline"}
      sessionId={runId}
      actions={
        <>
          {data ? (
            <Button appearance="secondary" onClick={() => setTab("questions")}>
              Resolve questions
            </Button>
          ) : null}
          <Button appearance="primary" onClick={() => navigate("/intake")}>
            New upload
          </Button>
        </>
      }
    >
      {q.isLoading ? (
        <div className={styles.skeletonBlock}>
          <Body1 style={{ color: tokens.colorNeutralForeground3 }}>Loading results…</Body1>
          <Skeleton aria-label="Loading">
            <SkeletonItem />
            <SkeletonItem />
            <SkeletonItem size={64} />
          </Skeleton>
        </div>
      ) : null}

      {q.isError ? (
        <MessageBar intent="error">
          <MessageBarBody>
            {runMissing
              ? "This run is no longer on the server (for example after the API reloaded). Start a new upload."
              : "Output is not ready yet, or the run failed. If the pipeline is still running, wait and refresh. Otherwise check the API logs."}
          </MessageBarBody>
        </MessageBar>
      ) : null}

      {data ? (
        <>
          <div className={styles.metaBar}>
            <div className={styles.statChips}>
              {typeof data.pipeline_duration_seconds === "number" ? (
                <Badge appearance="outline">{data.pipeline_duration_seconds.toFixed(1)}s</Badge>
              ) : null}
              {data.expected_completion_date ? (
                <Badge appearance="outline">Due {data.expected_completion_date}</Badge>
              ) : null}
              <Badge appearance="tint" color="informative">{reqs.length} reqs</Badge>
              <Badge appearance="tint" color="warning">{questions.length} questions</Badge>
              <Badge appearance="tint" color="important">{timeline.length} milestones</Badge>
            </div>
          </div>
          <div className={styles.tabSurface}>
            <TabList
              className={styles.tabList}
              selectedValue={tab}
              onTabSelect={(_, d) => setTab(d.value)}
              size="large"
              appearance="subtle"
            >
              <Tab value="summary" icon={<DocumentBulletListRegular />}>
                <span className={styles.tabLabel}>Summary &amp; scope</span>
              </Tab>
              <Tab value="timeline" icon={<DocumentDataRegular />}>
                <span className={styles.tabLabel}>
                  Timeline
                  <Badge
                    appearance={tab === "timeline" ? "filled" : "tint"}
                    color="important"
                    className={styles.tabCount}
                  >
                    {timeline.length}
                  </Badge>
                </span>
              </Tab>
              <Tab value="requirements" icon={<ClipboardTextLtrRegular />}>
                <span className={styles.tabLabel}>
                  Requirements
                  <Badge
                    appearance={tab === "requirements" ? "filled" : "tint"}
                    color="informative"
                    className={styles.tabCount}
                  >
                    {reqs.length}
                  </Badge>
                </span>
              </Tab>
              <Tab value="questions" icon={<QuestionCircleRegular />}>
                <span className={styles.tabLabel}>
                  Questions
                  <Badge
                    appearance={tab === "questions" ? "filled" : "tint"}
                    color="warning"
                    className={styles.tabCount}
                  >
                    {questions.length}
                  </Badge>
                </span>
              </Tab>
              <Tab value="draft" icon={<DocumentEditRegular />}>
                <span className={styles.tabLabel}>
                  Proposal draft
                  {sections.length > 0 ? (
                    <Badge
                      appearance={tab === "draft" ? "filled" : "tint"}
                      color="success"
                      className={styles.tabCount}
                    >
                      {sections.length}
                    </Badge>
                  ) : null}
                </span>
              </Tab>
              <Tab value="chat" icon={<ChatMultipleRegular />}>
                <span className={styles.tabLabel}>Clarification chat</span>
              </Tab>
            </TabList>
          </div>

          <div className={styles.tabContent}>
          {tab === "summary" && (data.summary || data.scope) ? (
            <div className={styles.section}>
              {data.summary ? (
                <>
                  <Title3 style={{ marginBottom: tokens.spacingVerticalM }}>Executive summary</Title3>
                  <div className={styles.summaryGrid}>
                    <SummaryCard
                      eyebrow="Recommendation"
                      title="Go / no-go"
                      body={data.summary.go_no_go_recommendation ?? "—"}
                      styles={styles}
                      icon={<FlagRegular fontSize={16} />}
                    />
                    <SummaryCard
                      eyebrow="Client"
                      title="Client overview"
                      body={data.summary.client_overview ?? "—"}
                      styles={styles}
                      icon={<BuildingRegular fontSize={16} />}
                    />
                    <SummaryCard
                      eyebrow="Strategy"
                      title="Strategic objectives"
                      body={data.summary.strategic_objectives ?? "—"}
                      styles={styles}
                      icon={<TargetRegular fontSize={16} />}
                    />
                    <SummaryCard
                      eyebrow="Evaluation"
                      title="Evaluation criteria"
                      body={data.summary.evaluation_criteria ?? "—"}
                      styles={styles}
                      icon={<ClipboardTextLtrRegular fontSize={16} />}
                    />
                    <SummaryCard
                      eyebrow="Approach"
                      title="Bid strategy"
                      body={data.summary.bid_strategy ?? "—"}
                      styles={styles}
                      icon={<LightbulbRegular fontSize={16} />}
                    />
                    <SummaryCard
                      eyebrow="Risks"
                      title="Risk flags"
                      styles={styles}
                      icon={<WarningRegular fontSize={16} />}
                      list={(data.summary.risk_flags ?? []).filter((k) => !/mock mode/i.test(k))}
                      emptyText="None noted."
                    />
                  </div>
                  {(data.summary.key_requirements ?? []).length > 0 ? (
                    <div className={styles.summaryCard} style={{ marginTop: tokens.spacingVerticalM }}>
                      <div className={styles.summaryHeader}>
                        <div className={styles.summaryIcon}>
                          <ClipboardTextLtrRegular fontSize={16} />
                        </div>
                        <div>
                          <Caption1 className={styles.summaryEyebrow}>Coverage</Caption1>
                          <Subtitle2 className={styles.summaryTitle}>Key requirements</Subtitle2>
                        </div>
                      </div>
                      <ul className={styles.bulletList}>
                        {(data.summary.key_requirements ?? []).map((k, i) => (
                          <li key={i}>{k}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </>
              ) : null}

              {data.scope ? (
                <>
                  <Divider style={{ marginTop: tokens.spacingVerticalXL, marginBottom: tokens.spacingVerticalL }} />

                  {(["business_requirements", "functional_requirements", "non_functional_requirements"] as const).map(
                    (key) => {
                      const label =
                        key === "business_requirements"
                          ? "Business requirements"
                          : key === "functional_requirements"
                            ? "Functional requirements"
                            : "Non-functional requirements";
                      const items = data.scope?.[key] ?? [];
                      if (items.length === 0) return null;
                      return (
                        <div key={key}>
                          <div className={styles.fieldLabel}>{label}</div>
                          <ul className={styles.list}>
                            {items.map((item, i) => (
                              <li key={item.requirement_id ?? `${key}-${i}`}>
                                <Body1>
                                  <strong>{item.requirement_id}:</strong> {item.text}
                                </Body1>
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    },
                  )}

                  {(data.scope.user_stories ?? []).length > 0 ? (
                    <>
                      <div className={styles.fieldLabel}>User stories</div>
                      {(data.scope.user_stories ?? []).map((us, i) => (
                        <Card
                          key={us.story_id ?? `us-${i}`}
                          appearance="outline"
                          style={{ marginBottom: 12 }}
                        >
                          <CardHeader
                            header={<Subtitle2>{us.story_id}</Subtitle2>}
                            description={<Body1>{us.story}</Body1>}
                          />
                        </Card>
                      ))}
                    </>
                  ) : null}

                  {data.scope.draft_scope_document ? (
                    <>
                      <div className={styles.fieldLabel}>Draft scope document</div>
                      <Body1 style={{ whiteSpace: "pre-wrap" }}>{data.scope.draft_scope_document}</Body1>
                    </>
                  ) : null}

                  {(data.scope.suggested_questions ?? []).length > 0 ? (
                    <>
                      <div className={styles.fieldLabel}>Suggested questions you may want to answer</div>
                      <ul className={styles.list}>
                        {(data.scope.suggested_questions ?? []).map((sq, i) => (
                          <li key={i}>
                            <Body1>{sq}</Body1>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                </>
              ) : null}
            </div>
          ) : null}

          {tab === "summary" && !data.summary && !data.scope ? (
            <Text className={styles.section}>No summary or scope in this response.</Text>
          ) : null}

          {tab === "chat" ? (
            <div className={styles.section}>
              <ClarificationChat
                runId={runId}
                initialSuggestions={data.scope?.suggested_questions ?? []}
              />
            </div>
          ) : null}

          {tab === "timeline" ? (
            <div className={styles.section}>
              <Title3 style={{ marginBottom: tokens.spacingVerticalS }}>Strict timeline table</Title3>
              <Body1
                style={{
                  display: "block",
                  marginBottom: tokens.spacingVerticalM,
                  color: tokens.colorNeutralForeground2,
                }}
              >
                Timelines are computed from the RFP submission date through expected completion.
              </Body1>
              <div className={styles.metaGrid} style={{ marginTop: 0, marginBottom: tokens.spacingVerticalM }}>
                <Caption1 className={styles.metaLabel}>Submission date</Caption1>
                <Text className={styles.metaValue}>{data.submission_date ?? "—"}</Text>
                <Caption1 className={styles.metaLabel}>Expected completion</Caption1>
                <Text className={styles.metaValue}>{data.expected_completion_date ?? "—"}</Text>
              </div>
              {timeline.length === 0 ? (
                <EmptyState title="No timeline milestones" description="The backend did not return timeline rows for this run." />
              ) : (
                <DataTable
                  ariaLabel="Strict timeline table"
                  columns={timelineColumns}
                  rows={timeline}
                  getRowKey={(row, idx) => `${row.milestone ?? "timeline"}-${idx}`}
                />
              )}
            </div>
          ) : null}

          {tab === "requirements" ? (
            <div className={styles.section}>
              {reqs.length === 0 ? (
                <EmptyState title="No requirements returned" description="Requirement extraction did not produce rows for this run." />
              ) : (
                <DataTable
                  ariaLabel="Requirements"
                  columns={requirementColumns}
                  rows={reqs}
                  getRowKey={(row, idx) => row.requirement_id ?? `req-${idx}`}
                />
              )}
            </div>
          ) : null}

          {tab === "questions" ? (
            <div className={styles.section}>
              <div className={styles.compactCard} style={{ marginBottom: tokens.spacingVerticalM }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                  <div>
                    <Subtitle2 style={{ margin: 0 }}>Resolve clarifications</Subtitle2>
                    <Caption1 style={{ display: "block", color: tokens.colorNeutralForeground3, marginTop: 2 }}>
                      Defaults are used automatically for any unanswered items.
                    </Caption1>
                  </div>
                  <Badge
                    appearance={answeredQuestions === questions.length && questions.length > 0 ? "filled" : "tint"}
                    color={answeredQuestions === questions.length && questions.length > 0 ? "success" : "warning"}
                  >
                    {answeredQuestions} of {questions.length} answered
                  </Badge>
                </div>
              </div>
              {questions.length === 0 ? (
                <EmptyState title="No clarifying questions" description="The clarification agent did not return question rows for this run." />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: tokens.spacingVerticalM }}>
                  {questions.map((qItem, qi) => {
                    const linkedReq = reqs.find((r) => r.requirement_id === qItem.source_requirement);
                    const qid = qItem.question_id ?? `q-${qi}`;
                    const suggestionOptions = possibleAnswerSuggestions(qItem, linkedReq);
                    const isAnswered = Boolean((answerByQuestion[qid] ?? "").trim());
                    return (
                      <div key={qid} className={styles.questionCard}>
                        <div className={styles.questionHeader}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "flex-start" }}>
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <Caption1 style={{ color: tokens.colorBrandForeground1, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
                                {qItem.question_id}
                                {qItem.source_requirement ? ` · ${qItem.source_requirement}` : ""}
                              </Caption1>
                              <Subtitle2 style={{ marginTop: 4, display: "block" }}>{qItem.question_text}</Subtitle2>
                              <div className={styles.questionMetaRow}>
                                {qItem.category ? <Badge appearance="tint" color="informative">{qItem.category}</Badge> : null}
                                {qItem.priority ? <Badge appearance="outline">{qItem.priority}</Badge> : null}
                                <Badge appearance={isAnswered ? "filled" : "outline"} color={isAnswered ? "success" : "subtle"}>
                                  {isAnswered ? "Answered" : "Awaiting answer"}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        </div>
                        <div className={styles.questionBody}>
                          {linkedReq?.text ? (
                            <div>
                              <span className={styles.inlineLabel}>Linked requirement</span>
                              <Body1 style={{ color: tokens.colorNeutralForeground2 }}>{linkedReq.text}</Body1>
                            </div>
                          ) : null}
                          {qItem.assumption_if_unanswered ? (
                            <div>
                              <span className={styles.inlineLabel}>Default assumption</span>
                              <Body1 style={{ color: tokens.colorNeutralForeground2 }}>{qItem.assumption_if_unanswered}</Body1>
                            </div>
                          ) : null}
                          <div>
                            <span className={styles.inlineLabel}>Suggested phrasings</span>
                            <div style={{ display: "grid", gap: tokens.spacingVerticalXS, marginTop: tokens.spacingVerticalXXS }}>
                              {suggestionOptions.map((suggestion, idx) => (
                                <Button
                                  key={`${qid}-sug-${idx}`}
                                  appearance="secondary"
                                  size="small"
                                  className={styles.suggestionPill}
                                  onClick={() =>
                                    setAnswerByQuestion((prev) => ({ ...prev, [qid]: suggestion }))
                                  }
                                >
                                  {suggestion}
                                </Button>
                              ))}
                            </div>
                          </div>
                          <div>
                            <span className={styles.inlineLabel}>Your answer</span>
                            <Textarea
                              value={answerByQuestion[qid] ?? ""}
                              placeholder="Final answer for this clarifying question..."
                              onChange={(_, d) =>
                                setAnswerByQuestion((prev) => ({ ...prev, [qid]: d.value }))
                              }
                              resize="vertical"
                              rows={3}
                              style={{ width: "100%" }}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              <div className={styles.submitCard}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "flex-start" }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <Caption1 style={{ color: tokens.colorBrandForeground1, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                      Final step
                    </Caption1>
                    <Subtitle2 style={{ display: "block", marginTop: 2 }}>
                      Create final proposal from all clarifications
                    </Subtitle2>
                    <Caption1 style={{ display: "block", color: tokens.colorNeutralForeground3, marginTop: 4 }}>
                      Submit answers now. If any answer is missing, default assumptions are used automatically.
                      The system then builds a clarification resolution document and regenerates the final draft.
                    </Caption1>
                  </div>
                  <Badge appearance={additionalFiles.length > 0 ? "filled" : "outline"} color={additionalFiles.length > 0 ? "brand" : "subtle"}>
                    {additionalFiles.length} file{additionalFiles.length === 1 ? "" : "s"} attached
                  </Badge>
                </div>
                <div style={{ marginTop: tokens.spacingVerticalM, display: "grid", gap: tokens.spacingVerticalM }}>
                  <div>
                    <span className={styles.inlineLabel}>Additional files (optional)</span>
                    <Caption1
                      style={{
                        display: "block",
                        color: tokens.colorNeutralForeground3,
                        marginTop: tokens.spacingVerticalXXS,
                        marginBottom: tokens.spacingVerticalXS,
                      }}
                    >
                      Upload supporting notes, pricing inputs, architecture docs, client answers, or reference material.
                      Supported formats: <code>.txt</code>, <code>.md</code>, <code>.doc</code>, <code>.docx</code>, <code>.pdf</code>, <code>.csv</code>.
                    </Caption1>
                    <input
                      type="file"
                      multiple
                      accept=".txt,.md,.doc,.docx,.pdf,.csv"
                      onChange={(e) => setAdditionalFiles(Array.from(e.target.files ?? []))}
                    />
                    {additionalFiles.length > 0 ? (
                      <Caption1 style={{ display: "block", marginTop: tokens.spacingVerticalXS, color: tokens.colorNeutralForeground2 }}>
                        Selected: {additionalFiles.map((file) => file.name).join(", ")}
                      </Caption1>
                    ) : null}
                  </div>
                  <Button
                    appearance="primary"
                    size="large"
                    disabled={resolveM.isPending || questions.length === 0}
                    onClick={() => resolveM.mutate()}
                  >
                    {resolveM.isPending ? "Creating new draft with changes..." : "Submit all answers and create new draft"}
                  </Button>
                  {resolveM.isSuccess ? (
                    <MessageBar intent="success">
                      <MessageBarBody>
                        {resolveM.data?.message ??
                          "Clarifications processed. New draft created with all submitted answers and defaults where needed."}
                      </MessageBarBody>
                    </MessageBar>
                  ) : null}
                  {resolveM.isError ? (
                    <MessageBar intent="error">
                      <MessageBarBody>
                        {resolveM.error ? getApiErrorMessage(resolveM.error) : "Failed to generate final outcome"}
                      </MessageBarBody>
                    </MessageBar>
                  ) : null}
                </div>
              </div>
              {clarificationDocument?.items?.length ? (
                <Card appearance="outline" style={{ marginTop: tokens.spacingVerticalL }}>
                  <CardHeader
                    header={<Subtitle2>Clarification resolution document</Subtitle2>}
                    description={<Caption1>Used directly as context for final draft generation.</Caption1>}
                  />
                  <div style={{ padding: `0 ${tokens.spacingHorizontalL} ${tokens.spacingVerticalL}` }}>
                    <Body1>
                      Generated at {clarificationDocument.generated_at ?? "—"} · Items{" "}
                      {clarificationDocument.items?.length ?? 0}
                    </Body1>
                    {(clarificationDocument.items ?? []).slice(0, 6).map((item, idx) => (
                      <div key={`${item.question_id ?? "item"}-${idx}`} style={{ marginTop: tokens.spacingVerticalS }}>
                        <Text size={200} weight="semibold">
                          {item.question_id}: {item.question_text}
                        </Text>
                        <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
                          Resolution ({item.resolution_source}): {item.final_resolution}
                        </Body1>
                      </div>
                    ))}
                  </div>
                </Card>
              ) : null}
            </div>
          ) : null}

          {tab === "draft" ? (
            <div className={`${styles.section} ${styles.draftShell}`}>
              <div className={styles.draftToolbar}>
                <div>
                  <Title3 style={{ margin: 0 }}>Final proposal document</Title3>
                  <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
                    Enterprise-ready response generated from RFP context, clarifications, and supporting files.
                  </Caption1>
                </div>
                <Button appearance="secondary" icon={<CopyRegular />} disabled={sections.length === 0} onClick={() => void copyDraft()}>
                  Copy draft
                </Button>
              </div>
              {sections.length === 0 ? (
                <EmptyState
                  title="No final draft yet"
                  description="Submit answers in the Questions tab to generate the enterprise proposal document."
                  actionLabel="Go to questions"
                  onAction={() => setTab("questions")}
                />
              ) : (
                <div className={styles.draftDocument}>
                  {sections.map((sec) => (
                    <DraftBody key={sec.section_id ?? sec.title} body={sec.body ?? ""} />
                  ))}
                </div>
              )}
            </div>
          ) : null}
          </div>
        </>
      ) : null}
    </MainPanel>
  );
}
