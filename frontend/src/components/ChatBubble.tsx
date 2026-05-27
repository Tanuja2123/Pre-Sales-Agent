import { makeStyles, mergeClasses, shorthands } from "@fluentui/react-components";
import type { ReactNode } from "react";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  row: {
    display: "flex",
    gap: "12px",
    marginBottom: "16px",
    maxWidth: "92%",
  },
  rowUser: {
    marginLeft: "auto",
    flexDirection: "row-reverse",
  },
  avatar: {
    width: "32px",
    height: "32px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "12px",
    fontWeight: 700,
    flexShrink: 0,
    fontFamily: pulse.fontSans,
  },
  avatarBot: {
    backgroundColor: pulse.tealDim,
    color: pulse.tealBright,
    border: `1px solid ${pulse.teal}`,
  },
  avatarUser: {
    backgroundColor: pulse.accentBlue,
    color: "#fff",
  },
  bubble: {
    ...shorthands.padding("14px", "18px"),
    borderRadius: "14px",
    fontSize: "14px",
    lineHeight: 1.55,
    fontFamily: pulse.fontSans,
  },
  bubbleBot: {
    backgroundColor: pulse.botBubble,
    color: pulse.text,
    border: `1px solid ${pulse.botBubbleBorder}`,
    borderTopLeftRadius: "4px",
  },
  bubbleUser: {
    backgroundColor: pulse.userBubble,
    color: pulse.text,
    border: `1px solid ${pulse.userBubbleBorder}`,
    borderTopRightRadius: "4px",
  },
});

type ChatBubbleProps = {
  role: "bot" | "user";
  children: ReactNode;
  avatarLabel?: string;
};

export function ChatBubble({ role, children, avatarLabel }: ChatBubbleProps) {
  const styles = useStyles();
  const isBot = role === "bot";
  const label = avatarLabel ?? (isBot ? "PS" : "You");

  return (
    <div className={mergeClasses(styles.row, !isBot && styles.rowUser)}>
      <div className={mergeClasses(styles.avatar, isBot ? styles.avatarBot : styles.avatarUser)}>{label}</div>
      <div className={mergeClasses(styles.bubble, isBot ? styles.bubbleBot : styles.bubbleUser)}>{children}</div>
    </div>
  );
}
