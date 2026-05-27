/** Parsed block for proposal draft section bodies. */
export type DraftBlock =
  | { type: "paragraph"; text: string }
  | { type: "heading"; level: number; text: string }
  | { type: "subheading"; text: string }
  | { type: "label"; label: string; value: string }
  | { type: "list"; items: string[] }
  | { type: "table"; rows: string[][] };

const PROPOSAL_SECTION_TITLES = new Set(
  [
    "Cover Page",
    "Executive Summary",
    "About the Company",
    "Understanding of Client Requirements",
    "Proposed Solution",
    "Scope of Work",
    "Project Timeline & Implementation Plan",
    "Team Structure",
    "Commercial Proposal / Pricing",
    "Risk Management",
    "Support & Maintenance",
    "Competitive Advantages",
    "Compliance Matrix",
    "Terms and Conditions",
    "Conclusion",
    "In-Scope Activities",
    "Out-of-Scope Activities",
    "Deliverables",
    "Milestones",
  ].map((s) => s.toLowerCase()),
);

/** Collapse tabs/multiple spaces; keep paragraph breaks. */
export function normalizeDraftText(body: string): string {
  return body
    .replace(/\r\n/g, "\n")
    .replace(/\t/g, " ")
    .replace(/[^\S\n]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function isProposalSectionTitle(text: string): boolean {
  const normalized = text.trim().toLowerCase();
  if (PROPOSAL_SECTION_TITLES.has(normalized)) return true;
  return PROPOSAL_SECTION_TITLES.has(normalized.replace(/^\d+\.\s*/, ""));
}

function isSubheadingLine(line: string): boolean {
  const text = line.trim();
  if (text.length < 3 || text.length > 72) return false;
  if (/[.!?]$/.test(text)) return false;
  if (text.includes("|")) return false;
  if (/^[-*•]\s/.test(text)) return false;
  if (/^#{1,3}\s/.test(text)) return false;
  if (/^\d+\.\s/.test(text) && isProposalSectionTitle(text)) return false;
  if (PROPOSAL_SECTION_TITLES.has(text.toLowerCase())) return true;
  if (/^[A-Z][A-Za-z0-9 &/'()-]+$/.test(text) && text.split(" ").length <= 8) return true;
  return false;
}

function parseLabelLine(line: string): { label: string; value: string } | null {
  const match = line.match(/^([^:]{2,48}):\s*(.+)$/);
  if (!match) return null;
  const label = match[1].trim();
  const value = match[2].trim();
  if (!value || label.length > 48) return null;
  if (/\s\*\s/.test(value)) return null;
  if (/\b(we|our|shall|will|must|propose|provide|ensure)\b/i.test(label)) return null;
  if (label.split(" ").length > 6) return null;
  return { label, value };
}

function splitInlineBullets(line: string): DraftBlock[] {
  const segments = line.split(/\s+\*\s+/).map((s) => s.trim()).filter(Boolean);
  if (segments.length <= 1) {
    return [{ type: "paragraph", text: line }];
  }
  const blocks: DraftBlock[] = [];
  const intro = segments[0];
  if (intro) {
    blocks.push({ type: "paragraph", text: intro });
  }
  const items = segments.slice(1);
  if (items.length) {
    blocks.push({ type: "list", items });
  }
  return blocks;
}

/** Turn LLM draft text into structured blocks with merged paragraphs. */
export function parseDraftBody(body: string): DraftBlock[] {
  const normalized = normalizeDraftText(body);
  if (!normalized) return [];

  const lines = normalized.split("\n").map((l) => l.trim());
  const blocks: DraftBlock[] = [];
  let pendingList: string[] = [];
  let pendingTable: string[][] = [];
  let pendingParagraph: string[] = [];

  const flushList = () => {
    if (pendingList.length) {
      blocks.push({ type: "list", items: [...pendingList] });
      pendingList = [];
    }
  };
  const flushTable = () => {
    if (pendingTable.length) {
      blocks.push({ type: "table", rows: [...pendingTable] });
      pendingTable = [];
    }
  };
  const flushParagraph = () => {
    if (!pendingParagraph.length) return;
    const text = pendingParagraph.join(" ").replace(/\s+/g, " ").trim();
    pendingParagraph = [];
    if (!text) return;
    if (/\s\*\s/.test(text)) {
      blocks.push(...splitInlineBullets(text));
      return;
    }
    blocks.push({ type: "paragraph", text });
  };

  for (const line of lines) {
    if (!line) {
      flushParagraph();
      flushList();
      flushTable();
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      flushTable();
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2].trim() });
      continue;
    }

    const numberedHeading = line.match(/^\d+\.\s+(.+)$/);
    if (numberedHeading && isProposalSectionTitle(numberedHeading[1])) {
      flushParagraph();
      flushList();
      flushTable();
      blocks.push({ type: "heading", level: 2, text: numberedHeading[1].trim() });
      continue;
    }

    if (line.startsWith("|") && line.endsWith("|")) {
      flushParagraph();
      flushList();
      const cells = line
        .slice(1, -1)
        .split("|")
        .map((cell) => cell.trim());
      const isDivider = cells.every((cell) => /^:?-{3,}:?$/.test(cell));
      if (!isDivider) {
        pendingTable.push(cells);
      }
      continue;
    }

    const bullet = line.match(/^[-*•]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      flushTable();
      pendingList.push(bullet[1].trim());
      continue;
    }

    flushList();
    flushTable();

    const boldHeading = line.match(/^\*\*(.+?)\*\*:?\s*$/);
    if (boldHeading) {
      flushParagraph();
      blocks.push({ type: "subheading", text: boldHeading[1].trim() });
      continue;
    }

    const label = parseLabelLine(line);
    if (label) {
      flushParagraph();
      blocks.push({ type: "label", label: label.label, value: label.value });
      continue;
    }

    if (isSubheadingLine(line)) {
      flushParagraph();
      blocks.push({ type: "subheading", text: line });
      continue;
    }

    pendingParagraph.push(line);
  }

  flushParagraph();
  flushList();
  flushTable();
  return blocks;
}
