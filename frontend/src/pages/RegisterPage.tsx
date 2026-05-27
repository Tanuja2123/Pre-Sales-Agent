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
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { getApiErrorMessage, fetchHealth, registerUser } from "../api/client";
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
  hint: {
    color: pulse.textDim,
    fontSize: "12px",
    lineHeight: 1.45,
  },
});

export function RegisterPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const registerM = useMutation({
    mutationFn: () =>
      registerUser({ full_name: fullName, email, password, confirm_password: confirmPassword }),
    onSuccess: async (data) => {
      const health = await fetchHealth();
      setSession(data.access_token, data.user, health.server_boot_id);
      navigate("/dashboard", { replace: true });
    },
  });

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault();
        registerM.mutate();
      }}
    >
      <Field label="Full name" required>
        <Input value={fullName} onChange={(_, d) => setFullName(d.value)} placeholder="Jane Doe" required />
      </Field>
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
          placeholder="At least 8 characters with a number"
          required
        />
      </Field>
      <CaptionHint />
      <Field label="Confirm password" required>
        <Input
          type="password"
          value={confirmPassword}
          onChange={(_, d) => setConfirmPassword(d.value)}
          placeholder="Re-enter password"
          required
        />
      </Field>
      {registerM.isError ? (
        <MessageBar intent="error">
          <MessageBarBody>{getApiErrorMessage(registerM.error)}</MessageBarBody>
        </MessageBar>
      ) : null}
      <div className={styles.actions}>
        <Button appearance="primary" type="submit" disabled={registerM.isPending}>
          {registerM.isPending ? "Creating account…" : "Create account"}
        </Button>
      </div>
      <Body1 className={styles.footer}>
        Already registered?{" "}
        <RouterLink to="/login" className={styles.link}>
          Sign in
        </RouterLink>
      </Body1>
    </form>
  );
}

function CaptionHint() {
  const styles = useStyles();
  return (
    <Body1 className={styles.hint}>
      Password must be at least 8 characters and include at least one letter and one number.
    </Body1>
  );
}
