import { Spinner, makeStyles } from "@fluentui/react-components";
import { useEffect, useState } from "react";
import { fetchHealth } from "../api/client";
import { useAuthStore } from "../stores/authStore";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  root: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    backgroundColor: pulse.bg,
  },
});

type AuthSessionGuardProps = {
  children: React.ReactNode;
};

/** Log out when the backend restarts (new server_boot_id) or is unreachable. */
export function AuthSessionGuard({ children }: AuthSessionGuardProps) {
  const styles = useStyles();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function validateSession() {
      const { isAuthenticated, serverBootId, logout, setServerBootId } = useAuthStore.getState();
      try {
        const health = await fetchHealth();
        const currentBootId = health.server_boot_id;
        if (!currentBootId) {
          if (isAuthenticated) logout();
          return;
        }
        if (isAuthenticated && serverBootId && serverBootId !== currentBootId) {
          logout();
        }
        setServerBootId(currentBootId);
      } catch {
        if (isAuthenticated) logout();
      } finally {
        if (!cancelled) setReady(true);
      }
    }

    void validateSession();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <div className={styles.root} aria-busy="true" aria-label="Checking session">
        <Spinner size="large" label="Loading…" />
      </div>
    );
  }

  return <>{children}</>;
}
