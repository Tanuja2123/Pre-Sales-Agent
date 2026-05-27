import { Caption1, makeStyles, shorthands, tokens } from "@fluentui/react-components";
import type { ReactNode } from "react";

const useStyles = makeStyles({
  root: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: tokens.spacingHorizontalM,
    flexWrap: "wrap",
    marginBottom: tokens.spacingVerticalL,
    ...shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalL),
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    backgroundColor: tokens.colorNeutralBackground1,
  },
  left: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    flexWrap: "wrap",
    minWidth: 0,
  },
  right: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    flexWrap: "wrap",
  },
  meta: {
    color: tokens.colorNeutralForeground3,
  },
});

type PageToolbarProps = {
  meta?: string;
  left?: ReactNode;
  right?: ReactNode;
};

export function PageToolbar({ meta, left, right }: PageToolbarProps) {
  const styles = useStyles();
  return (
    <div className={styles.root}>
      <div className={styles.left}>
        {left}
        {meta ? <Caption1 className={styles.meta}>{meta}</Caption1> : null}
      </div>
      <div className={styles.right}>{right}</div>
    </div>
  );
}
