import { Body1, makeStyles, shorthands, Text, Title2, Title3, tokens } from "@fluentui/react-components";
import { parseDraftBody } from "../utils/draftFormat";

const useStyles = makeStyles({
  article: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    maxWidth: "820px",
    lineHeight: 1.75,
  },
  paragraph: {
    lineHeight: 1.75,
    color: tokens.colorNeutralForeground2,
    marginTop: 0,
    marginBottom: tokens.spacingVerticalM,
    whiteSpace: "normal",
    wordBreak: "break-word",
    fontSize: tokens.fontSizeBase300,
  },
  heading1: {
    display: "block",
    marginTop: tokens.spacingVerticalXXL,
    marginBottom: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalS,
    color: tokens.colorNeutralForeground1,
    fontWeight: tokens.fontWeightBold,
    fontSize: tokens.fontSizeHero700,
    lineHeight: 1.25,
    borderBottom: `2px solid ${tokens.colorBrandStroke1}`,
    ":first-child": {
      marginTop: 0,
    },
  },
  heading2: {
    display: "block",
    marginTop: tokens.spacingVerticalXXL,
    marginBottom: tokens.spacingVerticalM,
    color: tokens.colorNeutralForeground1,
    fontWeight: tokens.fontWeightBold,
    fontSize: tokens.fontSizeBase600,
    lineHeight: 1.35,
    ":first-child": {
      marginTop: 0,
    },
  },
  heading3: {
    display: "block",
    marginTop: tokens.spacingVerticalXL,
    marginBottom: tokens.spacingVerticalS,
    color: tokens.colorNeutralForeground1,
    fontWeight: tokens.fontWeightBold,
    fontSize: tokens.fontSizeBase500,
    lineHeight: 1.4,
  },
  subheading: {
    display: "block",
    marginTop: tokens.spacingVerticalL,
    marginBottom: tokens.spacingVerticalS,
    color: tokens.colorNeutralForeground1,
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
    lineHeight: 1.4,
    letterSpacing: "0.01em",
  },
  labelRow: {
    display: "grid",
    gridTemplateColumns: "minmax(140px, 34%) 1fr",
    gap: tokens.spacingHorizontalL,
    alignItems: "start",
    marginBottom: tokens.spacingVerticalS,
    ...shorthands.padding(tokens.spacingVerticalS, 0),
    borderBottom: `1px solid ${tokens.colorNeutralStroke3}`,
  },
  labelKey: {
    color: tokens.colorNeutralForeground1,
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase300,
    lineHeight: 1.5,
  },
  labelValue: {
    color: tokens.colorNeutralForeground2,
    fontSize: tokens.fontSizeBase300,
    lineHeight: 1.65,
    wordBreak: "break-word",
  },
  tableWrap: {
    overflowX: "auto",
    marginTop: tokens.spacingVerticalL,
    marginBottom: tokens.spacingVerticalXL,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    color: tokens.colorNeutralForeground2,
  },
  tableCell: {
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    textAlign: "left",
    verticalAlign: "top",
    lineHeight: 1.55,
    fontSize: tokens.fontSizeBase300,
  },
  tableHeader: {
    backgroundColor: tokens.colorNeutralBackground3,
    color: tokens.colorNeutralForeground1,
    fontWeight: tokens.fontWeightSemibold,
  },
  list: {
    marginTop: tokens.spacingVerticalS,
    marginBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalXXL,
    color: tokens.colorNeutralForeground2,
    listStyleType: "disc",
    listStylePosition: "outside",
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  listItem: {
    lineHeight: 1.65,
    whiteSpace: "normal",
    wordBreak: "break-word",
    fontSize: tokens.fontSizeBase300,
  },
  winTheme: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    backgroundColor: tokens.colorPaletteMarigoldBackground2,
    borderLeft: `4px solid ${tokens.colorPaletteMarigoldBorder2}`,
    marginTop: tokens.spacingVerticalM,
    marginBottom: tokens.spacingVerticalL,
    borderRadius: tokens.borderRadiusMedium,
    lineHeight: 1.65,
    whiteSpace: "normal",
  },
});

type DraftBodyProps = {
  body: string;
};

function isMeaningfulCell(value: string | undefined): boolean {
  const text = (value ?? "").trim();
  return Boolean(text && text !== "—" && text !== "-" && text.toLowerCase() !== "n/a");
}

function visibleColumnIndexes(header: string[] | undefined, rows: string[][]): number[] {
  const maxColumns = Math.max(header?.length ?? 0, ...rows.map((row) => row.length));
  const indexes: number[] = [];
  for (let idx = 0; idx < maxColumns; idx += 1) {
    const hasBodyValue = rows.some((row) => isMeaningfulCell(row[idx]));
    if (hasBodyValue) {
      indexes.push(idx);
    }
  }
  return indexes;
}

export function DraftBody({ body }: DraftBodyProps) {
  const styles = useStyles();
  const blocks = parseDraftBody(body);

  if (!blocks.length) {
    return <Body1 className={styles.paragraph}>—</Body1>;
  }

  return (
    <article className={styles.article}>
      {blocks.map((block, i) => {
        if (block.type === "heading") {
          if (block.level === 1) {
            return (
              <Title2 key={`h-${i}`} className={styles.heading1}>
                {block.text}
              </Title2>
            );
          }
          if (block.level === 2) {
            return (
              <Title3 key={`h-${i}`} className={styles.heading2}>
                {block.text}
              </Title3>
            );
          }
          return (
            <Text key={`h-${i}`} as="h4" className={styles.heading3}>
              {block.text}
            </Text>
          );
        }

        if (block.type === "subheading") {
          return (
            <Text key={`sub-${i}`} as="h5" className={styles.subheading}>
              {block.text}
            </Text>
          );
        }

        if (block.type === "label") {
          return (
            <div key={`label-${i}`} className={styles.labelRow}>
              <Text className={styles.labelKey}>{block.label}</Text>
              <Text className={styles.labelValue}>{block.value}</Text>
            </div>
          );
        }

        if (block.type === "list") {
          return (
            <ul key={`ul-${i}`} className={styles.list}>
              {block.items.map((item, j) => (
                <li key={j} className={styles.listItem}>
                  {item}
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === "table") {
          const [header, ...rows] = block.rows;
          const visibleIndexes = visibleColumnIndexes(header, rows);
          const visibleHeader = header ? visibleIndexes.map((idx) => header[idx] ?? "") : undefined;
          const visibleRows = rows.map((row) => visibleIndexes.map((idx) => row[idx] ?? ""));
          if (visibleIndexes.length === 0) {
            return null;
          }
          return (
            <div key={`table-${i}`} className={styles.tableWrap}>
              <table className={styles.table}>
                {visibleHeader ? (
                  <thead>
                    <tr>
                      {visibleHeader.map((cell, j) => (
                        <th key={j} className={`${styles.tableCell} ${styles.tableHeader}`}>
                          {cell}
                        </th>
                      ))}
                    </tr>
                  </thead>
                ) : null}
                <tbody>
                  {visibleRows.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className={styles.tableCell}>
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        const text = block.text;
        if (text.includes("[WIN_THEME:")) {
          return (
            <div key={`p-${i}`} className={styles.winTheme}>
              {text}
            </div>
          );
        }

        return (
          <Body1 key={`p-${i}`} className={styles.paragraph}>
            {text}
          </Body1>
        );
      })}
    </article>
  );
}
