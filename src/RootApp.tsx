import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { Redirect, Route, Switch, useLocation } from "wouter";
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
  ResetPasswordPage,
  VerifyEmailPage,
} from "./features/auth/AuthPages";
import { AuthProvider } from "./features/auth/AuthProvider";
import { useAuth } from "./features/auth/auth-context";
import { CompetitionApp } from "./features/competition/CompetitionApp";
import { CareerApp } from "./features/career/CareerApp";
import { CmsApp } from "./features/cms/CmsApp";
import { PortalApp, RecruiterVerifyPage } from "./features/portals/PortalApp";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
  },
});

class WorkspaceErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Learner workspace rendering failed", error, info);
  }

  render() {
    if (this.state.failed)
      return (
        <main className="auth-page">
          <section className="auth-card" role="alert">
            <h1>The learner workspace could not be displayed.</h1>
            <p>
              Your saved work remains on the server. Reload to retry, and report
              the time of the error if it continues.
            </p>
            <button
              className="primary"
              onClick={() => window.location.reload()}
            >
              Reload workspace
            </button>
          </section>
        </main>
      );
    return this.props.children;
  }
}

function ProtectedWorkspace({
  portal = false,
  cms = false,
  career = false,
}: {
  portal?: boolean;
  cms?: boolean;
  career?: boolean;
}) {
  const { user, loading } = useAuth();
  const [location] = useLocation();
  if (loading)
    return (
      <main className="route-loading" role="status">
        Loading your secure workspace…
      </main>
    );
  if (!user)
    return <Redirect to={`/login?from=${encodeURIComponent(location)}`} />;
  if (cms) return <CmsApp />;
  if (career) return <CareerApp />;
  return portal ? <PortalApp /> : <CompetitionApp />;
}

function RouteTree() {
  return (
    <Switch>
      <Route path="/register" component={RegisterPage} />
      <Route path="/verify-email" component={VerifyEmailPage} />
      <Route path="/login" component={LoginPage} />
      <Route path="/forgot-password" component={ForgotPasswordPage} />
      <Route path="/reset-password" component={ResetPasswordPage} />
      <Route path="/verify/:shareToken">
        <RecruiterVerifyPage />
      </Route>
      <Route path="/academy/*?">
        <ProtectedWorkspace />
      </Route>
      <Route path="/career/*?">
        <ProtectedWorkspace career />
      </Route>
      <Route path="/cms/*?">
        <ProtectedWorkspace cms />
      </Route>
      <Route path="/instructor/*?">
        <ProtectedWorkspace portal />
      </Route>
      <Route path="/university/*?">
        <ProtectedWorkspace portal />
      </Route>
      <Route path="/company/*?">
        <ProtectedWorkspace portal />
      </Route>
      <Route path="/recruiter/*?">
        <ProtectedWorkspace portal />
      </Route>
      <Route path="/organization/*?">
        <ProtectedWorkspace portal />
      </Route>
      <Route path="/portfolio/sharing/*?">
        <ProtectedWorkspace portal />
      </Route>
      <Route path="/portfolio/preview/:shareId">
        <ProtectedWorkspace portal />
      </Route>
      <Route>
        <Redirect to="/login" />
      </Route>
    </Switch>
  );
}

export function RootApp() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WorkspaceErrorBoundary>
          <RouteTree />
        </WorkspaceErrorBoundary>
      </AuthProvider>
    </QueryClientProvider>
  );
}
