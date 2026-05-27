import {
  makeStyles,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  tokens,
} from "@fluentui/react-components";
import type { ReactNode } from "react";

const useStyles = makeStyles({
  wrap: {
    overflow: "auto",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    backgroundColor: tokens.colorNeutralBackground1,
  },
  table: {
    minWidth: "720px",
    width: "100%",
    tableLayout: "fixed",
  },
  cell: {
    paddingTop: tokens.spacingVerticalM,
    paddingBottom: tokens.spacingVerticalM,
    verticalAlign: "top",
    wordBreak: "break-word",
  },
  row: {
    ":hover": {
      backgroundColor: tokens.colorNeutralBackground2,
    },
  },
});

export type DataTableColumn<T> = {
  key: string;
  label: string;
  width?: string;
  render: (row: T, index: number) => ReactNode;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T, index: number) => string;
  ariaLabel: string;
};

function isMeaningful(value: ReactNode): boolean {
  if (value === null || value === undefined || value === false) return false;
  if (typeof value === "string") return Boolean(value.trim() && value.trim() !== "—");
  return true;
}

export function DataTable<T>({ columns, rows, getRowKey, ariaLabel }: DataTableProps<T>) {
  const styles = useStyles();
  const filtered = columns.filter((column) =>
    rows.some((row, index) => isMeaningful(column.render(row, index))),
  );
  // Never render a headerless table when rows exist (e.g. strict timeline milestones).
  const visibleColumns = rows.length > 0 && filtered.length === 0 ? columns : filtered;

  return (
    <div className={styles.wrap}>
      <Table aria-label={ariaLabel} size="small" className={styles.table}>
        <TableHeader>
          <TableRow>
            {visibleColumns.map((column) => (
              <TableHeaderCell key={column.key} style={{ width: column.width }}>
                {column.label}
              </TableHeaderCell>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={getRowKey(row, rowIndex)} className={styles.row}>
              {visibleColumns.map((column) => (
                <TableCell key={column.key} className={styles.cell}>
                  {column.render(row, rowIndex)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
