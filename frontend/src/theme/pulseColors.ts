/**
 * Enterprise slate + azure palette for the Pre-Sales Agent UI.
 *
 * Variable names are kept for backwards compatibility with the rest of the
 * codebase (e.g. `pulse.teal`), but the values now reflect a more restrained,
 * enterprise-grade color system: deep slate surfaces, an azure-blue primary
 * accent, and refined semantic colors that align with Fluent tokens.
 */
export const pulse = {
  bg: "#0b1220",
  bgGradient:
    "radial-gradient(1200px 600px at 0% -10%, rgba(59,130,246,0.10), transparent 60%), radial-gradient(900px 500px at 100% 0%, rgba(99,102,241,0.08), transparent 55%), #0b1220",
  sidebar: "#0a1120",
  sidebarBorder: "#1b2741",
  panel: "#0f172a",
  panelElevated: "#162033",
  panelRaised: "#1b2640",
  panelBorder: "#26334d",
  panelBorderStrong: "#324166",
  /** Primary brand accent (azure blue). */
  teal: "#3b82f6",
  tealBright: "#60a5fa",
  tealDim: "#1e40af",
  tealGlow: "rgba(59, 130, 246, 0.14)",
  text: "#e6ebf5",
  textMuted: "#a1abc2",
  textDim: "#6f7a92",
  botBubble: "#131c30",
  botBubbleBorder: "#2a3855",
  userBubble: "#16284a",
  userBubbleBorder: "#2f4a7b",
  /** Secondary accent for informational badges and tiles. */
  accentBlue: "#6366f1",
  accentSky: "#0ea5e9",
  accentViolet: "#8b5cf6",
  success: "#10b981",
  warning: "#f59e0b",
  danger: "#ef4444",
  inputBg: "#0d172a",
  shadowSoft: "0 10px 30px -12px rgba(2, 6, 23, 0.65), 0 4px 12px -6px rgba(2, 6, 23, 0.45)",
  shadowLift: "0 18px 48px -16px rgba(2, 6, 23, 0.75), 0 8px 16px -8px rgba(2, 6, 23, 0.55)",
  ring: "0 0 0 1px rgba(59, 130, 246, 0.45)",
  fontSans: '"Segoe UI", "Inter", system-ui, sans-serif',
  fontMono: '"Cascadia Code", "Fira Code", ui-monospace, monospace',
} as const;

export const PIPELINE_STAGES = [
  { id: "ingest", label: "Ingestion", to: 20 },
  { id: "understand", label: "Understanding", to: 40 },
  { id: "summarize", label: "Summarization", to: 60 },
  { id: "clarify", label: "Clarification", to: 80 },
  { id: "draft", label: "AI proposal draft", to: 100 },
] as const;
