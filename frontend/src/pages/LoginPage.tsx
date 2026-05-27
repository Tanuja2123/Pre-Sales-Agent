import {
  Body1,
  Button,
  Field,
  Input,
  MessageBar,
  MessageBarBody,
  makeStyles,
} from "@fluentui/react-components";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { getApiErrorMessage, fetchHealth, loginUser } from "../api/client";
import { useAuthStore } from "../stores/authStore";
import { pulse } from "../theme/pulseColors";

const useStyles = makeStyles({
  form: {
    display: "grid",
    gap: "14px",
  },
  actions: {
    display: "grid",
    gap: "10px",
    marginTop: "8px",
  },
  footer: {
    marginTop: "16px",
    textAlign: "center",
    color: pulse.textMuted,
    fontSize: "13px",
  },
  link: {
    color: pulse.tealBright,
    textDecoration: "none",
    ":hover": { textDecoration: "underline" },
  },
});

export function LoginPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const loginM = useMutation({
    mutationFn: () => loginUser({ email, password }),
    onSuccess: async (data) => {
      const health = await fetchHealth();
      setSession(data.access_token, data.user, health.server_boot_id);
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(from && from !== "/login" && from !== "/register" ? from : "/dashboard", { replace: true });
    },
  });

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault();
        loginM.mutate();
      }}
    >
      <Field label="Email address" required>
        <Input
          type="email"
          value={email}
          onChange={(_, d) => setEmail(d.value)}
          placeholder="you@company.com"
          required
        />
      </Field>
      <Field label="Password" required>
        <Input
          type="password"
          value={password}
          onChange={(_, d) => setPassword(d.value)}
          placeholder="Enter your password"
          required
        />
      </Field>
      {loginM.isError ? (
        <MessageBar intent="error">
          <MessageBarBody>{getApiErrorMessage(loginM.error)}</MessageBarBody>
        </MessageBar>
      ) : null}
      <div className={styles.actions}>
        <Button appearance="primary" type="submit" disabled={loginM.isPending}>
          {loginM.isPending ? "Signing in…" : "Sign in"}
        </Button>
        <Button appearance="secondary" type="button" disabled={loginM.isPending} onClick={() => navigate("/register")}>
          Create account
        </Button>
      </div>
      <Body1 className={styles.footer}>
        No account?{" "}
        <RouterLink to="/register" className={styles.link}>
          Create one
        </RouterLink>
      </Body1>
    </form>
  );
}
