import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Redirect, useLocation } from "wouter";
import { ShieldCheck } from "lucide-react";
import { apiFetch, ApiError } from "../../lib/api-client";
import { useAuth } from "./auth-context";

function AuthShell({
  title,
  intro,
  children,
}: {
  title: string;
  intro: string;
  children: ReactNode;
}) {
  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <Link className="auth-brand" to="/">
          <ShieldCheck aria-hidden="true" /> CyberMentor AI
        </Link>
        <span className="kicker">BUILD. DEFEND. SUCCEED.</span>
        <h1 id="auth-title">{title}</h1>
        <p>{intro}</p>
        {children}
      </section>
    </main>
  );
}

function ErrorSummary({ error }: { error: string }) {
  return (
    <div className="form-error" role="alert" tabIndex={-1}>
      {error}
    </div>
  );
}

export function LoginPage() {
  const [, navigate] = useLocation();
  const { user, refresh } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Redirect to="/academy" />;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      await apiFetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          password: data.get("password"),
        }),
      });
      await refresh();
      navigate("/academy", { replace: true });
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Sign-in failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <AuthShell
      title="Return to your investigation."
      intro="Sign in with your verified learner identity."
    >
      {error && <ErrorSummary error={error} />}
      <form className="auth-form" onSubmit={submit}>
        <label>
          Email
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="auth-links">
        <Link to="/forgot-password">Forgot password?</Link>
        <Link to="/register">Create learner account</Link>
      </div>
    </AuthShell>
  );
}

export function RegisterPage() {
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          display_name: data.get("displayName"),
          email: data.get("email"),
          password: data.get("password"),
        }),
      });
      setSubmitted(true);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Registration failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <AuthShell
      title="Create your learner identity."
      intro="Your personal workspace keeps progress and evidence isolated."
    >
      {submitted ? (
        <div className="form-success" role="status">
          Registration accepted. Open the verification link delivered by the
          configured email service (the local server output in console mode),
          then <Link to="/login">sign in</Link>.
        </div>
      ) : (
        <>
          {error && <ErrorSummary error={error} />}
          <form className="auth-form" onSubmit={submit}>
            <label>
              Display name
              <input name="displayName" autoComplete="name" required />
            </label>
            <label>
              Email
              <input name="email" type="email" autoComplete="email" required />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                minLength={12}
                autoComplete="new-password"
                aria-describedby="password-help"
                required
              />
            </label>
            <small id="password-help">
              At least 12 characters using three of: uppercase, lowercase,
              number, symbol.
            </small>
            <button className="primary" disabled={busy}>
              {busy ? "Creating account…" : "Create account"}
            </button>
          </form>
        </>
      )}
      <div className="auth-links">
        <Link to="/login">Already registered?</Link>
      </div>
    </AuthShell>
  );
}

export function VerifyEmailPage() {
  const params = new URLSearchParams(window.location.search);
  const [state, setState] = useState<"ready" | "busy" | "done" | "error">(
    params.get("token") ? "ready" : "error",
  );
  const [message, setMessage] = useState(
    params.get("token") ? "" : "The verification token is missing.",
  );
  async function verify() {
    setState("busy");
    try {
      const response = await apiFetch<{ message: string }>(
        "/api/v1/auth/verify-email",
        {
          method: "POST",
          body: JSON.stringify({ token: params.get("token") }),
        },
      );
      setMessage(response.message);
      setState("done");
    } catch (caught) {
      setMessage(
        caught instanceof ApiError ? caught.message : "Verification failed.",
      );
      setState("error");
    }
  }
  return (
    <AuthShell
      title="Verify your email."
      intro="Verification binds progress and evidence to your learner identity."
    >
      {state === "ready" && (
        <button className="primary" onClick={verify}>
          Verify email
        </button>
      )}
      {state === "busy" && <p role="status">Verifying…</p>}
      {(state === "done" || state === "error") && (
        <div
          className={state === "done" ? "form-success" : "form-error"}
          role="status"
        >
          {message} {state === "done" && <Link to="/login">Sign in</Link>}
        </div>
      )}
    </AuthShell>
  );
}

export function ForgotPasswordPage() {
  const [done, setDone] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await apiFetch("/api/v1/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email: data.get("email") }),
    });
    setDone(true);
  }
  return (
    <AuthShell
      title="Recover your account."
      intro="Recovery responses do not disclose whether an account exists."
    >
      {done ? (
        <div className="form-success" role="status">
          If the account exists, a reset message has been sent.
        </div>
      ) : (
        <form className="auth-form" onSubmit={submit}>
          <label>
            Email
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <button className="primary">Send reset link</button>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPasswordPage() {
  const params = new URLSearchParams(window.location.search);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const token = params.get("token");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await apiFetch("/api/v1/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password: data.get("password") }),
      });
      setDone(true);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Password reset failed.",
      );
    }
  }
  return (
    <AuthShell
      title="Choose a new password."
      intro="Using a reset link revokes existing sessions for this account."
    >
      {!token ? (
        <ErrorSummary error="The reset token is missing." />
      ) : done ? (
        <div className="form-success" role="status">
          Password updated. <Link to="/login">Sign in</Link>.
        </div>
      ) : (
        <>
          {error && <ErrorSummary error={error} />}
          <form className="auth-form" onSubmit={submit}>
            <label>
              New password
              <input
                name="password"
                type="password"
                minLength={12}
                autoComplete="new-password"
                required
              />
            </label>
            <button className="primary">Reset password</button>
          </form>
        </>
      )}
    </AuthShell>
  );
}
