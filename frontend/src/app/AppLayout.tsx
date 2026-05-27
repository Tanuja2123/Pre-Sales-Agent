import { makeStyles } from "@fluentui/react-components";
import { Outlet } from "react-router-dom";
import { PipelineSidebar } from "../components/PipelineSidebar";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  root: {
    display: "flex",
    minHeight: "100vh",
    backgroundColor: pulse.bg,
  },
});

export function AppLayout() {
  const styles = useStyles();
  return (
    <div className={styles.root}>
      <PipelineSidebar />
      <Outlet />
    </div>
  );
}
