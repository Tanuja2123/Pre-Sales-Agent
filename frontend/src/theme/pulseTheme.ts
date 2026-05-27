import {
  BrandVariants,
  createDarkTheme,
  type Theme,
} from "@fluentui/react-components";

/**
 * Enterprise azure-blue brand ramp.
 *
 * Drives Fluent primary surfaces (buttons, badges, focus rings, etc.).
 * Tuned for a dark slate shell and good contrast at the higher steps used
 * by Fluent for `appearance="primary"` controls.
 */
const pulseBrand: BrandVariants = {
  10: "#020817",
  20: "#0a172e",
  30: "#0f2247",
  40: "#142d65",
  50: "#1b3a86",
  60: "#2553ad",
  70: "#3b82f6",
  80: "#60a5fa",
  90: "#93c5fd",
  100: "#bfdbfe",
  110: "#dbeafe",
  120: "#e6f0fe",
  130: "#eff5ff",
  140: "#f5f9ff",
  150: "#fafcff",
  160: "#ffffff",
};

export const pulseDarkTheme: Theme = createDarkTheme(pulseBrand);
