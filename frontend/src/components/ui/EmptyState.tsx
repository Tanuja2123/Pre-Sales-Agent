import { Body1, Button, makeStyles, shorthands, Subtitle2, tokens } from "@fluentui/react-components";
import type { ReactNode } from "react";

const useStyles = makeStyles({
  root: {
    display: "grid",
    justifyItems: "center",
    gap: tokens.spacingVerticalS,
    textAlign: "center",
    color: tokens.colorNeutralForeground3,
    ...shorthands.padding(tokens.spacingVerticalXXL, tokens.spacingHorizontalXL),
    border: `1px dashed ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    backgroundColor: tokens.colorNeutralBackground2,
  },
  icon: {
    fontSize: "36px",
    color: tokens.colorBrandForeground1,
  },
});

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  const styles = useStyles();
  return (
    <div className={styles.root}>
      {icon ? <div className={styles.icon}>{icon}</div> : null}
      <Subtitle2>{title}</Subtitle2>
      {description ? <Body1>{description}</Body1> : null}
      {actionLabel && onAction ? (
        <Button appearance="primary" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
