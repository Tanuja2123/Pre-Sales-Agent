import type { FluentIcon } from "@fluentui/react-icons";
import {
  ChatBubblesQuestionRegular,
  DocumentBulletListRegular,
  DocumentDataRegular,
  PenSparkleRegular,
  TextBulletListSquareRegular,
} from "@fluentui/react-icons";
import { PIPELINE_STAGES } from "../theme/pulseColors";

export type AgentId = (typeof PIPELINE_STAGES)[number]["id"];

export type AgentDefinition = {
  id: AgentId;
  name: string;
  shortName: string;
  tagline: string;
  description: string;
  inputs: string[];
  outputs: string[];
  progressTo: number;
  Icon: FluentIcon;
  accent: string;
};

export const AGENTS: AgentDefinition[] = [
  {
    id: "ingest",
    name: "Ingestion Agent",
    shortName: "Ingestion",
    tagline: "Parse · chunk · index",
    description:
      "Extracts text from PDF, DOCX, or TXT uploads, splits the RFP into overlapping chunks for retrieval, and indexes them for the proposal draft step.",
    inputs: ["Uploaded RFP file"],
    outputs: ["Structured document", "Text chunks", "Section map"],
    progressTo: 20,
    Icon: DocumentDataRegular,
    accent: "#3b82f6",
  },
  {
    id: "understand",
    name: "Understanding Agent",
    shortName: "Understanding",
    tagline: "Requirements extraction",
    description:
      "Uses Groq to extract structured requirements with IDs, priority, MAF classification, and ambiguity scores from the full RFP text.",
    inputs: ["Parsed RFP text"],
    outputs: ["Requirement list (REQ-###)"],
    progressTo: 40,
    Icon: TextBulletListSquareRegular,
    accent: "#6366f1",
  },
  {
    id: "summarize",
    name: "Summarization Agent",
    shortName: "Summarization",
    tagline: "Executive intelligence",
    description:
      "Produces client overview, strategic objectives, bid strategy, risks, and a go / no-go recommendation for pursuit decisions.",
    inputs: ["RFP + requirements"],
    outputs: ["Executive summary JSON"],
    progressTo: 60,
    Icon: DocumentBulletListRegular,
    accent: "#0ea5e9",
  },
  {
    id: "clarify",
    name: "Clarification Agent",
    shortName: "Clarification",
    tagline: "Client-ready questions",
    description:
      "Generates clarifying questions tied to specific requirements, with assumptions if the client does not respond before bid finalization.",
    inputs: ["Structured requirements"],
    outputs: ["Question set with assumptions"],
    progressTo: 80,
    Icon: ChatBubblesQuestionRegular,
    accent: "#f59e0b",
  },
  {
    id: "draft",
    name: "Response Draft Agent",
    shortName: "Proposal draft",
    tagline: "RAG-backed proposal",
    description:
      "Drafts multi-section proposal content with Groq, using retrieved RFP chunks and mandatory requirement coverage for compliance sections.",
    inputs: ["Summary", "Requirements", "RAG snippets"],
    outputs: ["Proposal sections (S-1…S-n)"],
    progressTo: 100,
    Icon: PenSparkleRegular,
    accent: "#10b981",
  },
];

export function getAgent(id: string): AgentDefinition | undefined {
  return AGENTS.find((a) => a.id === id);
}

export function agentWorkspacePath(agentId: AgentId, runId?: string): string {
  if (runId) return `/run/${runId}/agents/${agentId}`;
  return `/agents/${agentId}`;
}
