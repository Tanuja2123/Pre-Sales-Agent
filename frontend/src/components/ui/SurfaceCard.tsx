import { makeStyles, shorthands, tokens } from "@fluentui/react-components";
import type { ReactNode } from "react";

const useStyles = makeStyles({
  root: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    boxShadow: tokens.shadow2,
    ...shorthands.padding(tokens.spacingVerticalL, tokens.spacingHorizontalL),
  },
  compact: {
    ...shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalM),
  },
});

type SurfaceCardProps = {
  children: ReactNode;
  compact?: boolean;
  className?: string;
};

export function SurfaceCard({ children, compact = false, className }: SurfaceCardProps) {
  const styles = useStyles();
  return <section className={[styles.root, compact ? styles.compact : "", className ?? ""].join(" ")}>{children}</section>;
}
