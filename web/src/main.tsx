import React, { useEffect, useId, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDown,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Braces,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  Circle,
  Clock3,
  Code2,
  ExternalLink,
  Eye,
  EyeOff,
  FileCheck2,
  FileJson,
  Fingerprint,
  GitBranch,
  Globe2,
  HeartPulse,
  HelpCircle,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  Menu,
  Play,
  Plus,
  Radar,
  RefreshCw,
  Search,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Terminal,
  Users,
  Waypoints,
  X,
} from "lucide-react";
import "./styles.css";

type User = { id: string; name: string; email: string };
type Session = { user: User | null; demo: boolean };
type Stage = { id: string; status: string; detail: string };
type RunEvent = {
  id: string;
  at: string;
  stage: string;
  title: string;
  detail: string;
  kind: string;
  evidence?: unknown;
  hash: string;
  previousHash: string;
};
type Artifact = { name: string; type: string; sha256: string; url?: string };
type Run = {
  id: string;
  scenario: string;
  title: string;
  status: string;
  createdAt: string;
  completedAt?: string;
  stage: string;
  events: RunEvent[];
  metrics: {
    durationMs: number;
    testsPassed: number;
    testsTotal: number;
    requestsReplayed: number;
    duplicateCharges: number;
    modelCalls: number;
    artifactsReused: number;
  };
  before: { revision: string; healthStatus: string; contractStatus: string };
  after: { revision: string; healthStatus: string; contractStatus: string };
  artifacts: Artifact[];
  diff: { path: string; before: string; after: string };
  stages: Stage[];
  decision: { outcome: string; reason: string };
  integrations?: { issueUrl?: string; mrUrl?: string; pipelineUrl?: string };
};
type Contract = {
  id: string;
  name: string;
  description: string;
  status: string;
  source: string;
  category: string;
};
type Overview = {
  project: { name: string; environment: string };
  runs: Run[];
  contracts: Contract[];
  metrics: {
    totalRuns: number;
    recovered: number;
    blocked: number;
    protectedRequests: number;
  };
  integration: { mode: string; gitlabConfigured: boolean };
  policy: {
    autonomy: string;
    maxAttempts: number;
    allowedPaths: string[];
    [key: string]: unknown;
  };
};
type Route = { page: Nav; runId?: string };
type Nav = "overview" | "runs" | "promises" | "gitlab" | "policy";
type GitLabEvidence = {
  projectUrl: string;
  flowUrl: string;
  issueUrl: string;
  sessionUrl: string;
  checkedAt: string;
  pipelines: {
    id: number;
    status: string;
    sha: string;
    url: string;
    ref: string;
  }[];
  mergeRequests: {
    iid: number;
    title: string;
    state: string;
    url: string;
    sourceBranch: string;
    sha: string;
  }[];
  available: boolean;
  detail: string;
  stale?: boolean;
};
const stageNames = [
  "plan",
  "create",
  "verify",
  "package",
  "secure",
  "release",
  "configure",
  "monitor",
  "govern",
];
const scenarios = [
  {
    id: "duplicate-charge",
    icon: CheckCheck,
    label: "The double charge",
    tag: "RECOMMENDED",
    description:
      "An otherwise healthy checkout charges the same customer twice after a retry.",
    promise: "One purchase. One charge.",
    path: "Detect → repair → replay → reconcile",
  },
  {
    id: "tenant-leak",
    icon: Users,
    label: "The invisible data leak",
    tag: "ISOLATION",
    description:
      "A green service exposes one workspace’s order to another workspace.",
    promise: "Your customer data stays yours.",
    path: "Detect → contain → repair → prove isolation",
  },
  {
    id: "unsafe-repair",
    icon: Shield,
    label: "The repair that must stop",
    tag: "SAFETY",
    description:
      "A proposed fix requests forbidden execution capabilities. The controller must block it before the code runs.",
    promise: "A recovery never bypasses the rules.",
    path: "Detect → inspect unsafe code → block execution",
  },
];
class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message.replaceAll("\u2014", ", "));
    this.name = "ApiError";
    this.status = status;
  }
}
async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), 15000);
  const cancel = () => controller.abort("cancelled");
  signal?.addEventListener("abort", cancel, { once: true });
  try {
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
      headers:
        body === undefined
          ? { Accept: "application/json" }
          : { "Content-Type": "application/json", Accept: "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const value = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401 && !path.startsWith("/api/auth/"))
        window.dispatchEvent(new Event("aftercare:session-ended"));
      const validation = Array.isArray(value?.detail)
        ? value.detail
            .map(
              (item: { loc?: string[]; msg?: string }) =>
                `${item.loc?.at(-1) || "Input"}: ${item.msg || "Check this value"}`,
            )
            .join(". ")
        : "";
      throw new ApiError(
        typeof value?.detail === "string"
          ? value.detail
          : typeof value?.error === "string"
            ? value.error
            : validation ||
              `Request failed (${response.status}). Please try again.`,
        response.status,
      );
    }
    if (!value || typeof value !== "object")
      throw new ApiError(
        "The server returned an unexpected response. Please refresh and try again.",
      );
    return value as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted)
      throw new ApiError(
        controller.signal.reason === "cancelled"
          ? "Request cancelled."
          : "The request timed out. If a recovery was starting, refresh its status before trying again.",
      );
    throw new ApiError(
      "Unable to reach Aftercare. Check your connection, then try again.",
    );
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", cancel);
  }
}
function currentRoute(): Route {
  const path = window.location.hash.replace(/^#\/?/, "").split("/");
  const pages: Nav[] = ["overview", "runs", "promises", "gitlab", "policy"];
  const page = pages.includes(path[0] as Nav) ? (path[0] as Nav) : "overview";
  return {
    page,
    runId:
      page === "runs" && /^[a-zA-Z0-9-]{1,100}$/.test(path[1] || "")
        ? path[1]
        : undefined,
  };
}
function setRoute(page: Nav, runId?: string) {
  window.location.hash = `/${page}${runId ? `/${encodeURIComponent(runId)}` : ""}`;
}
function short(value?: string) {
  return value ? value.slice(0, 8) : "Not yet";
}
function date(value: string) {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
function duration(ms?: number) {
  return ms === undefined
    ? "Not yet"
    : ms === 0
      ? "0s"
      : ms < 1000
        ? `${ms} ms`
        : `${(ms / 1000).toFixed(1)}s`;
}
function Status({
  value,
  compact = false,
}: {
  value: string;
  compact?: boolean;
}) {
  const label =
    value === "running" ? "In progress" : value.replace(/[-_]/g, " ");
  return (
    <span className={`status status-${value} ${compact ? "compact" : ""}`}>
      {value === "running" ? (
        <LoaderCircle size={12} className="spin" />
      ) : (
        <span className="status-dot" />
      )}
      {label}
    </span>
  );
}
function Brand({ dark = false }: { dark?: boolean }) {
  return (
    <div className={`brand ${dark ? "brand-dark" : ""}`}>
      <span className="brand-symbol">
        <Activity size={23} strokeWidth={2.2} />
      </span>
      <span>
        aftercare<span className="brand-period">.</span>
      </span>
    </div>
  );
}
function Button({
  children,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={`button ${className}`} {...props}>
      {children}
    </button>
  );
}
function ErrorNotice({
  error,
  onClose,
}: {
  error: string;
  onClose?: () => void;
}) {
  return (
    <div className="error-notice" role="alert">
      <Shield size={17} />
      <span>{error}</span>
      {onClose && (
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Dismiss error"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
function Modal({
  title,
  onClose,
  children,
  wide = false,
  canClose = true,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
  canClose?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const close = useRef(onClose);
  const closeAllowed = useRef(canClose);
  closeAllowed.current = canClose;
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const frame = requestAnimationFrame(() =>
      (
        ref.current?.querySelector<HTMLElement>("[data-autofocus]") ||
        ref.current
      )?.focus(),
    );
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && closeAllowed.current) {
        e.preventDefault();
        close.current();
      }
      if (e.key === "Tab" && ref.current) {
        const elements = Array.from(
          ref.current.querySelectorAll<HTMLElement>(
            'button, input, a[href], [tabindex="0"]',
          ),
        ).filter(
          (el) =>
            !el.hasAttribute("disabled") && el.getClientRects().length > 0,
        );
        const first = elements[0];
        const last = elements.at(-1);
        if (!first) {
          e.preventDefault();
          ref.current.focus();
        } else if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === ref.current)
        ) {
          e.preventDefault();
          last?.focus();
        } else if (
          !e.shiftKey &&
          (document.activeElement === last ||
            document.activeElement === ref.current)
        ) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", key);
      document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && closeAllowed.current)
          close.current();
      }}
    >
      <div
        ref={ref}
        className={`modal ${wide ? "modal-wide" : ""}`}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="modal-heading">
          <div>
            <div className="eyebrow">AFTERCARE / CONTROL ROOM</div>
            <h2 id={titleId}>{title}</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close dialog"
            disabled={!canClose}
            onClick={() => close.current()}
          >
            <X size={21} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
function Landing({
  onSession,
  notice = "",
}: {
  onSession: (s: Session) => void;
  notice?: string;
}) {
  const [auth, setAuth] = useState<null | "login" | "register">(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function sandbox() {
    setBusy(true);
    setError("");
    try {
      const s = await api<Session>("/api/demo/session", {});
      setRoute("overview");
      onSession(s.user ? s : await api<Session>("/api/session"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="landing">
      <button
        className="skip-link"
        onClick={() => document.getElementById("main-content")?.focus()}
      >
        Skip to content
      </button>
      {notice && (
        <div className="session-notice" role="status">
          <LockKeyhole size={15} />
          {notice}
        </div>
      )}
      <header className="landing-nav">
        <a href="#" aria-label="Aftercare home">
          <Brand />
        </a>
        <div className="landing-nav-right">
          <span className="mini-tag">CUSTOMER SAFETY AFTER EVERY RELEASE</span>
          <Button className="button-quiet" onClick={() => setAuth("login")}>
            Sign in <ArrowRight size={15} />
          </Button>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        <section className="landing-hero">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="orange-line" /> CUSTOMER-PROMISE RELEASE RECOVERY
            </div>
            <h1>
              Your health check
              <br />
              is green.
              <br />
              <em>
                Your customer was
                <br />
                charged twice.
              </em>
            </h1>
            <p className="hero-intro">
              Release assurance for engineering teams shipping payments and
              shared workspaces. Catch broken customer promises, test a bounded
              repair, and keep the evidence.
            </p>
            <div className="hero-actions">
              <Button
                className="button-orange button-large"
                onClick={sandbox}
                disabled={busy}
              >
                {busy ? (
                  <LoaderCircle className="spin" size={18} />
                ) : (
                  <Play size={16} fill="currentColor" />
                )}{" "}
                {busy ? "Preparing your sandbox…" : "Open sandbox"}
                <ArrowRight size={17} />
              </Button>
              <button className="text-link" onClick={() => setAuth("register")}>
                Create an account <ChevronRight size={16} />
              </button>
            </div>
            <div className="hero-note">
              <LockKeyhole size={13} /> Isolated, synthetic data. No account or
              API key needed.
            </div>
            {error && (
              <ErrorNotice error={error} onClose={() => setError("")} />
            )}
          </div>
          <div
            className="hero-visual"
            aria-label="Illustration of a healthy release that violates a customer promise"
          >
            <div className="visual-top">
              <span>
                <span className="live-dot" /> RELEASE / 8F3A2C1
              </span>
              <span className="mono">01</span>
            </div>
            <div className="release-card">
              <div className="release-card-icon">
                <HeartPulse size={24} />
              </div>
              <div>
                <span className="eyebrow">THE SYSTEM SAYS</span>
                <h3>Everything is healthy.</h3>
                <span className="release-test">
                  <Check size={13} /> Health endpoint 200 OK
                </span>
              </div>
              <span className="pill-green">PASS</span>
            </div>
            <div className="visual-connector">
              <span />
              <ArrowDown size={17} />
              <span />
            </div>
            <div className="promise-visual">
              <div className="promise-visual-top">
                <span className="eyebrow">THE CUSTOMER EXPERIENCES</span>
                <span className="small-warning">PROMISE BROKEN</span>
              </div>
              <div className="receipt">
                <div>
                  <span className="receipt-item">Order #1024</span>
                  <strong>One purchase.</strong>
                </div>
                <div className="receipt-lines">
                  <div>
                    <span>Charge 01</span>
                    <span>₹2,400</span>
                  </div>
                  <div className="duplicate-line">
                    <span>
                      Charge 02 <span>duplicate</span>
                    </span>
                    <span>₹2,400</span>
                  </div>
                </div>
              </div>
              <div className="visual-fix">
                <span className="brand-symbol small">
                  <Activity size={18} />
                </span>
                <span>
                  Keep the promise.
                  <br />
                  <strong>Close the recovery loop.</strong>
                </span>
                <ArrowRight size={24} />
              </div>
            </div>
            <div className="visual-bottom">
              <span>DETECT</span>
              <span>REPAIR</span>
              <span>PROVE</span>
              <span>RECONCILE</span>
            </div>
            <p className="illustration-label">
              Illustrative scenario · launch an isolated recovery
            </p>
          </div>
        </section>
        <section className="landing-proof" id="how-it-works">
          <div>
            <span className="eyebrow">BEYOND UPTIME</span>
            <h2>
              Don’t just roll back the code.
              <br />
              Make the customer whole.
            </h2>
          </div>
          <div className="landing-steps">
            {[
              {
                n: "01",
                title: "Name the promise",
                detail:
                  "Encode what customers rely on: one charge per order, tenant isolation, and a bounded recovery.",
              },
              {
                n: "02",
                title: "Let the loop work",
                detail:
                  "An isolated recovery executes real tests, policy gates, packaging, release checks, and synthetic reconciliation.",
              },
              {
                n: "03",
                title: "Take the proof with you",
                detail:
                  "Inspect the code diff, every stage, and a hash-linked evidence trail. See exactly why it shipped or stopped.",
              },
            ].map((step) => (
              <div key={step.n}>
                <span className="step-number">{step.n}</span>
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="landing-trust">
          <ShieldCheck size={20} />
          <p>
            <strong>Autonomy with boundaries.</strong> The sandbox runs a
            deterministic reference controller. GitLab Duo provides agent
            reasoning in the connected flow. Execution evidence tells you which
            mode ran.
          </p>
          <span className="mono">NINE STAGES. ONE ACCOUNTABLE LOOP.</span>
        </section>
      </main>
      <footer className="landing-footer">
        <Brand />
        <span>Designed & built by Shivam Gupta</span>
        <span className="mono">KEEP THE CUSTOMER PROMISE.</span>
      </footer>
      {auth && (
        <AuthModal
          mode={auth}
          setMode={setAuth}
          onClose={() => setAuth(null)}
          onSession={onSession}
        />
      )}
    </div>
  );
}
function AuthModal({
  mode,
  setMode,
  onClose,
  onSession,
}: {
  mode: "login" | "register";
  setMode: (mode: "login" | "register") => void;
  onClose: () => void;
  onSession: (s: Session) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const hintId = useId();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const s = await api<Session>(`/api/auth/${mode}`, {
        name: name.trim(),
        email: email.trim(),
        password,
      });
      setRoute("overview");
      onSession(s.user ? s : await api<Session>("/api/session"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={
        mode === "register" ? "Your own recovery workspace." : "Welcome back."
      }
      canClose={!busy}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <p className="muted">
        {mode === "register"
          ? "Save future recovery runs and evidence in a private account workspace."
          : "Sign in to inspect your recovery history and evidence."}
      </p>
      <form onSubmit={submit} className="auth-form" aria-busy={busy}>
        {mode === "register" && (
          <label>
            Your name
            <input
              required
              data-autofocus
              autoComplete="name"
              value={name}
              disabled={busy}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              maxLength={80}
            />
          </label>
        )}
        <label>
          Email address
          <input
            required
            data-autofocus={mode === "login" ? "" : undefined}
            type="email"
            autoComplete="email"
            value={email}
            disabled={busy}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            maxLength={254}
          />
        </label>
        <label>
          Password
          <span className="password-input">
            <input
              required
              type={visible ? "text" : "password"}
              autoComplete={
                mode === "register" ? "new-password" : "current-password"
              }
              minLength={10}
              maxLength={128}
              value={password}
              disabled={busy}
              onChange={(e) => setPassword(e.target.value)}
              aria-describedby={mode === "register" ? hintId : undefined}
              placeholder={
                mode === "register" ? "At least 10 characters" : "Your password"
              }
            />
            <button
              type="button"
              className="password-toggle"
              onClick={() => setVisible(!visible)}
              aria-label={visible ? "Hide password" : "Show password"}
              aria-pressed={visible}
              disabled={busy}
            >
              {visible ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </span>
        </label>
        {mode === "register" && (
          <p id={hintId} className="form-hint">
            <LockKeyhole size={13} />
            Use at least 10 characters. Guest sandbox runs stay in the guest
            workspace and do not transfer to this account.
          </p>
        )}
        {error && <ErrorNotice error={error} />}
        <Button
          type="submit"
          disabled={busy}
          className="button-primary full-width"
        >
          {busy && <LoaderCircle size={16} className="spin" />}
          {busy
            ? mode === "register"
              ? "Creating your workspace…"
              : "Signing in…"
            : mode === "register"
              ? "Create account"
              : "Sign in"}
          <ArrowRight size={17} />
        </Button>
      </form>
      <p className="auth-switch">
        {mode === "register" ? "Already have an account?" : "New to Aftercare?"}{" "}
        <button
          disabled={busy}
          onClick={() => {
            setMode(mode === "register" ? "login" : "register");
            setError("");
            setPassword("");
            setVisible(false);
          }}
        >
          {mode === "register" ? "Sign in" : "Create account"}
        </button>
      </p>
    </Modal>
  );
}
function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialError, setInitialError] = useState("");
  const [notice, setNotice] = useState("");
  const load = async () => {
    setLoading(true);
    setInitialError("");
    try {
      setSession(await api<Session>("/api/session"));
    } catch (e) {
      setInitialError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
    const ended = () => {
      setSession({ user: null, demo: false });
      setNotice(
        "Your session ended. Sign in again or open a new isolated sandbox.",
      );
      setRoute("overview");
    };
    window.addEventListener("aftercare:session-ended", ended);
    return () => window.removeEventListener("aftercare:session-ended", ended);
  }, []);
  if (loading)
    return (
      <div className="app-loading">
        <Brand />
        <LoaderCircle size={24} className="spin" />
        <p>Opening the control room…</p>
      </div>
    );
  if (initialError)
    return (
      <div className="app-loading">
        <Brand />
        <ErrorNotice error={initialError} />
        <Button onClick={load}>
          <RefreshCw size={16} />
          Retry connection
        </Button>
      </div>
    );
  if (!session?.user)
    return (
      <Landing
        onSession={(s) => {
          setNotice("");
          setSession(s);
        }}
        notice={notice}
      />
    );
  return (
    <Workspace key={session.user.id} session={session} onSession={setSession} />
  );
}
function Workspace({
  session,
  onSession,
}: {
  session: Session;
  onSession: (s: Session) => void;
}) {
  const [nav, setNav] = useState<Nav>(currentRoute().page);
  const [runLoading, setRunLoading] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const mobileTrigger = useRef<HTMLButtonElement>(null);
  const headingRef = useRef<HTMLElement>(null);
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Run | null>(null);
  const [scenarioOpen, setScenarioOpen] = useState(false);
  const [chosenScenario, setChosenScenario] = useState("duplicate-charge");
  const [help, setHelp] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [starting, setStarting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [auth, setAuth] = useState<"login" | "register" | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const refresh = async () => {
    setRefreshing(true);
    try {
      setData(await api<Overview>("/api/overview"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  };
  useEffect(() => {
    void refresh();
  }, []);
  useEffect(() => {
    let active = true;
    let request = 0;
    const sync = async () => {
      const route = currentRoute();
      const version = ++request;
      setNav(route.page);
      setMobile(false);
      setError("");
      if (!route.runId) {
        setSelected(null);
        setRunLoading(false);
        return;
      }
      setRunLoading(true);
      setSelected((previous) =>
        previous?.id === route.runId ? previous : null,
      );
      try {
        const run = await api<Run>(
          `/api/runs/${encodeURIComponent(route.runId)}`,
        );
        if (active && version === request) setSelected(run);
      } catch (e) {
        if (active && version === request) setError((e as Error).message);
      } finally {
        if (active && version === request) setRunLoading(false);
      }
    };
    void sync();
    window.addEventListener("hashchange", sync);
    return () => {
      active = false;
      window.removeEventListener("hashchange", sync);
    };
  }, []);
  useEffect(() => {
    if (!mobile) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const frame = requestAnimationFrame(() =>
      sidebarRef.current?.querySelector<HTMLElement>("button")?.focus(),
    );
    const closeOnDesktop = () => {
      if (window.innerWidth > 760) setMobile(false);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setMobile(false);
      }
      if (e.key === "Tab" && sidebarRef.current) {
        const controls = Array.from(
          sidebarRef.current.querySelectorAll<HTMLElement>("button, a[href]"),
        ).filter(
          (el) =>
            el.getClientRects().length > 0 && !el.hasAttribute("disabled"),
        );
        const first = controls[0];
        const last = controls.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    window.addEventListener("resize", closeOnDesktop);
    document.addEventListener("keydown", key);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", closeOnDesktop);
      document.removeEventListener("keydown", key);
      document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus();
    };
  }, [mobile]);
  useEffect(() => {
    if (!selected || selected.status !== "running") return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const run = await api<Run>(
          `/api/runs/${encodeURIComponent(selected.id)}`,
        );
        if (!active) return;
        setSelected(run);
        setError("");
        if (run.status !== "running") await refresh();
        else timer = setTimeout(tick, 1200);
      } catch (e) {
        if (active) {
          setError((e as Error).message);
          timer = setTimeout(tick, 2500);
        }
      }
    };
    timer = setTimeout(tick, 1000);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [selected?.id, selected?.status]);
  useEffect(() => {
    if (
      selected?.status === "running" ||
      !data?.runs.some((r) => r.status === "running")
    )
      return;
    const timer = setTimeout(() => void refresh(), 1200);
    return () => clearTimeout(timer);
  }, [data, selected?.status]);
  async function start(scenario: string) {
    setStarting(true);
    setError("");
    try {
      const run = await api<Run>("/api/runs", { scenario });
      setSelected(run);
      setNav("runs");
      setRoute("runs", run.id);
      setScenarioOpen(false);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStarting(false);
    }
  }
  async function openRun(run: Run) {
    setSelected(run);
    setNav("runs");
    setRoute("runs", run.id);
  }
  async function logout() {
    setLoggingOut(true);
    try {
      await api("/api/auth/logout", {});
      setRoute("overview");
      onSession({ user: null, demo: false });
    } catch (e) {
      setError((e as Error).message);
      setLoggingOut(false);
    }
  }
  function navigate(page: Nav) {
    setRoute(page);
    setNav(page);
    setSelected(null);
    setMobile(false);
    window.scrollTo({ top: 0 });
    requestAnimationFrame(() => headingRef.current?.focus());
  }
  const activeRun = data?.runs.find((run) => run.status === "running");
  const chosen =
    scenarios.find((scenario) => scenario.id === chosenScenario) ||
    scenarios[0];
  const connected =
    data?.integration.gitlabConfigured && data?.integration.mode === "gitlab";
  return (
    <div className="workspace">
      <button className="skip-link" onClick={() => headingRef.current?.focus()}>
        Skip to workspace content
      </button>
      <aside
        ref={sidebarRef}
        id="workspace-navigation"
        aria-label="Workspace navigation"
        role={mobile ? "dialog" : undefined}
        aria-modal={mobile ? true : undefined}
        className={`sidebar ${mobile ? "sidebar-open" : ""}`}
      >
        <div className="sidebar-brand">
          <Brand dark />
          <button
            className="icon-button mobile-close"
            aria-label="Close navigation"
            onClick={() => setMobile(false)}
          >
            <X size={19} />
          </button>
        </div>
        <div className="workspace-selector">
          <span className="project-monogram">
            {session.demo
              ? "A"
              : (session.user?.name || "A").slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>
              {session.demo
                ? "Aftercare release lab"
                : `${session.user?.name?.split(" ")[0] || "Your"}’s release lab`}
            </strong>
            <span>
              {session.demo ? "Guest sandbox workspace" : "Personal workspace"}
            </span>
          </div>
        </div>
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {[
            { id: "overview", name: "Overview", icon: LayoutDashboard },
            { id: "runs", name: "Recovery runs", icon: Waypoints },
            { id: "promises", name: "Customer promises", icon: HeartPulse },
            { id: "gitlab", name: "GitLab workflow", icon: GitBranch },
            {
              id: "policy",
              name: "Policy & connections",
              icon: SlidersHorizontal,
            },
          ].map((item) => (
            <button
              key={item.id}
              aria-current={nav === item.id ? "page" : undefined}
              className={`nav-item ${nav === item.id ? "active" : ""}`}
              onClick={() => navigate(item.id as Nav)}
            >
              <item.icon size={18} />
              <span>{item.name}</span>
              {item.id === "runs" && !!data?.runs.length && (
                <span className="nav-count">{data.runs.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <div>
              <span className="live-dot" />
              <strong>
                {connected ? "Connected GitLab flow" : "Reference controller"}
              </strong>
            </div>
            <p>
              {connected
                ? "Review linked execution evidence in every recovery run."
                : "Real sandbox execution. No live customer or production mutations."}
            </p>
            <button onClick={() => setHelp(true)}>
              Understand execution modes <ArrowRight size={13} />
            </button>
          </div>
          <button className="sidebar-help" onClick={() => setHelp(true)}>
            <BookOpen size={17} /> How Aftercare works
            <ExternalLink size={13} />
          </button>
          <div className="profile">
            <span className="avatar">
              {(session.user?.name || "Guest").slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong>
                {session.demo ? "Sandbox explorer" : session.user?.name}
              </strong>
              <span>
                {session.demo ? "Isolated guest session" : session.user?.email}
              </span>
            </div>
            <button
              className="icon-button"
              aria-label="Sign out"
              title="Sign out"
              disabled={loggingOut}
              onClick={logout}
            >
              {loggingOut ? (
                <LoaderCircle className="spin" size={17} />
              ) : (
                <LogOut size={17} />
              )}
            </button>
          </div>
        </div>
      </aside>
      {mobile && (
        <button
          className="sidebar-scrim"
          aria-label="Close menu"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="workspace-main">
        <header className="topbar">
          <div>
            <button
              ref={mobileTrigger}
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              aria-controls="workspace-navigation"
              aria-expanded={mobile}
              onClick={() => setMobile(true)}
            >
              <Menu size={21} />
            </button>
            <span className="topbar-home">Workspace</span>
            <ChevronRight size={13} />
            <strong>
              {
                {
                  overview: "Overview",
                  runs: "Recovery runs",
                  promises: "Customer promises",
                  gitlab: "GitLab workflow",
                  policy: "Policy & connections",
                }[nav]
              }
            </strong>
            {selected && (
              <>
                <ChevronRight size={13} />
                <span className="mono">{short(selected.id)}</span>
              </>
            )}
          </div>
          <div>
            <span className="environment-tag">
              <span className="live-dot" />
              {session.demo ? "GUEST SANDBOX" : "ISOLATED SANDBOX"}
            </span>
            <button
              className="icon-button"
              onClick={() => setHelp(true)}
              aria-label="About execution modes"
            >
              <HelpCircle size={18} />
            </button>
          </div>
        </header>
        <main
          ref={headingRef}
          id="workspace-content"
          tabIndex={-1}
          className="main-content"
        >
          {error && <ErrorNotice error={error} onClose={() => setError("")} />}
          {!data ? (
            <div className="content-loading">
              <LoaderCircle size={25} className="spin" />
              <h3>Loading your workspace</h3>
              <p>
                {error
                  ? "Your workspace could not be loaded. Check your connection and try again."
                  : "Checking recovery history and customer promises."}
              </p>
              <Button onClick={refresh} disabled={refreshing}>
                Retry connection
              </Button>
            </div>
          ) : (
            <>
              {session.demo && (
                <div className="sandbox-banner">
                  <FlaskIcon />
                  <p>
                    <strong>
                      A real recovery. A safe place to break things.
                    </strong>{" "}
                    Runs execute in your isolated sandbox with synthetic
                    customers.
                  </p>
                  <button onClick={() => setAuth("register")}>
                    Create account <ArrowRight size={14} />
                  </button>
                </div>
              )}
              {nav === "overview" && (
                <OverviewPage
                  data={data}
                  onStart={() => setScenarioOpen(true)}
                  onRun={openRun}
                  onPromises={() => navigate("promises")}
                  onRuns={() => navigate("runs")}
                />
              )}
              {nav === "runs" &&
                (runLoading && !selected ? (
                  <div className="content-loading" role="status">
                    <LoaderCircle size={25} className="spin" />
                    <h3>Loading recovery evidence</h3>
                    <p>Fetching this run from your workspace.</p>
                  </div>
                ) : selected ? (
                  <RunDetail
                    key={selected.id}
                    run={selected}
                    onBack={() => {
                      navigate("runs");
                      void refresh();
                    }}
                    onStart={() => setScenarioOpen(true)}
                    onError={setError}
                  />
                ) : (
                  <RunsPage
                    runs={data.runs}
                    onStart={() => setScenarioOpen(true)}
                    onRun={openRun}
                    onRefresh={refresh}
                    refreshing={refreshing}
                  />
                ))}
              {nav === "promises" && (
                <PromisesPage
                  contracts={data.contracts}
                  onStart={() => setScenarioOpen(true)}
                />
              )}
              {nav === "gitlab" && <GitLabWorkflowPage />}
              {nav === "policy" && (
                <PolicyPage
                  data={data}
                  onHelp={() => setHelp(true)}
                  onGitLab={() => navigate("gitlab")}
                />
              )}
            </>
          )}
          <footer className="app-footer">
            <span>
              <span className="brand-word">aftercare.</span> Keep the customer
              promise.
            </span>
            <span>
              Built by Shivam Gupta <span className="footer-divider">/</span>{" "}
              Customer-promise release assurance
            </span>
          </footer>
        </main>
      </div>
      {scenarioOpen && (
        <Modal
          title="Put a promise to the test."
          canClose={!starting}
          onClose={() => {
            if (!starting) setScenarioOpen(false);
          }}
          wide
        >
          <p className="muted modal-description">
            Choose a controlled fault, then start the recovery. Your isolated
            workspace runs real checks and records the decision. No production
            system is connected.
          </p>
          {activeRun && (
            <div className="active-recovery-notice" role="status">
              <LoaderCircle size={18} className="spin" />
              <div>
                <strong>A recovery is already running.</strong>
                <p>Wait for it to finish before introducing another fault.</p>
              </div>
              <Button
                onClick={() => {
                  setScenarioOpen(false);
                  void openRun(activeRun);
                }}
              >
                View active recovery
                <ArrowRight size={14} />
              </Button>
            </div>
          )}
          <div className="scenario-modal-error">
            {error && (
              <ErrorNotice error={error} onClose={() => setError("")} />
            )}
          </div>
          <div
            className="scenario-list"
            role="radiogroup"
            aria-label="Recovery scenario"
          >
            {scenarios.map((s) => (
              <button
                type="button"
                role="radio"
                aria-checked={chosenScenario === s.id}
                disabled={starting || !!activeRun}
                className={`scenario-option ${chosenScenario === s.id ? "scenario-selected" : ""}`}
                key={s.id}
                onClick={() => setChosenScenario(s.id)}
                onKeyDown={(event) => {
                  if (
                    [
                      "ArrowDown",
                      "ArrowRight",
                      "ArrowUp",
                      "ArrowLeft",
                    ].includes(event.key)
                  ) {
                    event.preventDefault();
                    const direction = ["ArrowDown", "ArrowRight"].includes(
                      event.key,
                    )
                      ? 1
                      : -1;
                    const next =
                      scenarios[
                        (scenarios.findIndex((item) => item.id === s.id) +
                          direction +
                          scenarios.length) %
                          scenarios.length
                      ];
                    setChosenScenario(next.id);
                    const buttons =
                      event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>(
                        '[role="radio"]',
                      );
                    buttons?.[
                      scenarios.findIndex((item) => item.id === next.id)
                    ]?.focus();
                  }
                }}
                tabIndex={chosenScenario === s.id ? 0 : -1}
              >
                <span className="scenario-icon">
                  <s.icon size={23} />
                </span>
                <span className="scenario-copy">
                  <span className="scenario-title">
                    {s.label}
                    <span className="scenario-tag">{s.tag}</span>
                  </span>
                  <span>{s.description}</span>
                  <span className="scenario-promise">Promise: {s.promise}</span>
                </span>
                <span className="scenario-radio">
                  {chosenScenario === s.id && <Check size={12} />}
                </span>
              </button>
            ))}
          </div>
          <div className="scenario-expectation">
            <ShieldCheck size={18} />
            <div>
              <strong>
                {chosenScenario === "unsafe-repair"
                  ? "Expected safe outcome: blocked repair"
                  : "Expected safe outcome: recovered promise"}
              </strong>
              <p>
                {chosenScenario === "unsafe-repair"
                  ? "The forbidden candidate must never execute. The verified safe revision stays active, with the rejection recorded."
                  : "The faulty behavior must reproduce, a verified safe revision must take over, and the scoped repair must pass contracts and the HTTP stability gate."}
              </p>
              <span className="scenario-path">{chosen.path}</span>
            </div>
          </div>
          <div className="scenario-launch">
            <span>
              <Clock3 size={14} />
              Includes a five-second stability observation
            </span>
            <Button
              className="button-primary"
              disabled={starting || !!activeRun}
              onClick={() => void start(chosenScenario)}
            >
              {starting ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Play size={14} />
              )}
              {starting ? "Starting recovery…" : "Start selected recovery"}
              <ArrowRight size={15} />
            </Button>
          </div>
          <div className="modal-footnote">
            <LockKeyhole size={15} /> No production credentials. No real
            charges. Results belong to this isolated execution.
          </div>
        </Modal>
      )}
      {help && (
        <HelpModal onClose={() => setHelp(false)} connected={!!connected} />
      )}
      {auth && (
        <AuthModal
          mode={auth}
          setMode={setAuth}
          onClose={() => setAuth(null)}
          onSession={(s) => {
            onSession(s);
            setAuth(null);
          }}
        />
      )}
    </div>
  );
}
function FlaskIcon() {
  return <Braces size={19} />;
}
function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
function OverviewPage({
  data,
  onStart,
  onRun,
  onPromises,
  onRuns,
}: {
  data: Overview;
  onStart: () => void;
  onRun: (r: Run) => void;
  onPromises: () => void;
  onRuns: () => void;
}) {
  const running = data.runs.find((r) => r.status === "running");
  const latest = data.runs[0];
  return (
    <>
      <PageHeading
        eyebrow="RELEASE ASSURANCE / OVERVIEW"
        title="The release is just the beginning."
        description="One accountable loop from broken promise to proven recovery."
        action={
          <Button className="button-primary" onClick={onStart}>
            <Plus size={16} />
            Start a recovery
          </Button>
        }
      />
      <section className="overview-hero">
        <div className="overview-hero-copy">
          <span className="eyebrow">
            <span className="live-dot" /> BEYOND THE GREEN CHECK
          </span>
          <h2>
            Healthy infrastructure.
            <br />
            <em>Unhappy customer?</em>
          </h2>
          <p>
            A passing health check won’t catch a double charge. Give your
            release a customer promise to keep, and an inspectable path to
            recovery.
          </p>
          <Button onClick={onStart} className="button-cream">
            {data.metrics.totalRuns
              ? "Launch a recovery"
              : "Run your first recovery"}{" "}
            <ArrowRight size={16} />
          </Button>
        </div>
        <div className="hero-diagram">
          <div className="diagram-row">
            <HeartPulse size={17} />
            <span>Service health</span>
            <span className="diagram-value">
              <Check size={12} /> 200 OK
            </span>
          </div>
          <div className="diagram-row diagram-row-alert">
            <CheckCheck size={17} />
            <span>One order → one charge</span>
            <span className="diagram-value">?</span>
          </div>
          <div className="diagram-bridge">
            <span />
            <Activity size={24} />
            <span />
          </div>
          <div className="diagram-outcome">
            <span className="small-label">AFTERCARE CLOSES THE GAP</span>
            <strong>Detect. Repair. Prove. Reconcile.</strong>
            <span>Customer outcomes become release gates.</span>
          </div>
        </div>
      </section>
      <section className="metrics-grid" aria-label="Actual recovery metrics">
        {[
          {
            label: "Recovery runs",
            value: data.metrics.totalRuns,
            icon: Waypoints,
            note: "Actual sandbox executions",
          },
          {
            label: "Recovered",
            value: data.metrics.recovered,
            icon: ShieldCheck,
            note: "Customer promises restored",
          },
          {
            label: "Safely blocked",
            value: data.metrics.blocked,
            icon: LockKeyhole,
            note: "Unsafe changes stopped",
          },
          {
            label: "HTTP checks executed",
            value: data.metrics.protectedRequests,
            icon: CheckCheck,
            note: "Completed recovery validation traffic",
          },
        ].map((metric) => (
          <div className="metric-card" key={metric.label}>
            <div>
              <span>{metric.label}</span>
              <metric.icon size={17} />
            </div>
            <strong>{metric.value.toLocaleString()}</strong>
            <span className="metric-note">{metric.note}</span>
          </div>
        ))}
      </section>
      <div className="overview-bottom">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">RECOVERY ACTIVITY</span>
              <h2>
                {running
                  ? "Recovery in progress"
                  : latest
                    ? "Latest recovery"
                    : "Your first proof starts here."}
              </h2>
            </div>
            <button className="text-link" onClick={onRuns}>
              All runs <ArrowRight size={14} />
            </button>
          </div>
          {latest ? (
            <button
              className="latest-run"
              onClick={() => onRun(running || latest)}
            >
              <div className="run-icon">
                <Waypoints size={23} />
              </div>
              <div>
                <strong>{(running || latest).title}</strong>
                <span>
                  {date((running || latest).createdAt)} ·{" "}
                  <span className="mono">{short((running || latest).id)}</span>
                </span>
              </div>
              <Status value={(running || latest).status} />
              <ChevronRight size={18} />
            </button>
          ) : (
            <div className="empty-activity">
              <span className="empty-orbit">
                <Waypoints size={30} />
              </span>
              <div>
                <h3>No recoveries yet.</h3>
                <p>
                  Introduce a fault. Watch the loop earn your trust, one
                  evidence-backed decision at a time.
                </p>
                <button className="text-link" onClick={onStart}>
                  Start an isolated recovery <ArrowRight size={15} />
                </button>
              </div>
            </div>
          )}
          <div className="stage-coverage">
            <span className="eyebrow">THE COMPLETE LOOP</span>
            <div>
              {stageNames.map((stage, i) => (
                <React.Fragment key={stage}>
                  <span>{stage}</span>
                  {i !== stageNames.length - 1 && <ChevronRight size={10} />}
                </React.Fragment>
              ))}
            </div>
          </div>
        </section>
        <section className="panel promise-summary">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">WHAT YOU PROTECT</span>
              <h2>Customer promises</h2>
            </div>
            <HeartPulse size={20} />
          </div>
          <div>
            {data.contracts.slice(0, 3).map((contract, i) => (
              <button
                className="promise-summary-row"
                key={contract.id}
                onClick={onPromises}
              >
                <span className="promise-number">0{i + 1}</span>
                <span>
                  <strong>{contract.name}</strong>
                  <small>{contract.category}</small>
                </span>
                <ChevronRight size={15} />
              </button>
            ))}
          </div>
          <button className="text-link" onClick={onPromises}>
            Inspect promise contracts <ArrowRight size={14} />
          </button>
        </section>
      </div>
    </>
  );
}
function RunsPage({
  runs,
  onStart,
  onRun,
  onRefresh,
  refreshing,
}: {
  runs: Run[];
  onStart: () => void;
  onRun: (r: Run) => void;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const visible = runs.filter(
    (run) =>
      (filter === "all" || run.status === filter) &&
      `${run.title} ${run.id} ${run.scenario}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  return (
    <>
      <PageHeading
        eyebrow="EXECUTION HISTORY"
        title="Every decision leaves a trace."
        description="Real recovery runs. Inspect the evidence, understand the outcome."
        action={
          <Button className="button-primary" onClick={onStart}>
            <Plus size={16} />
            Start a recovery
          </Button>
        }
      />
      <div className="panel">
        <div className="runs-search">
          <Search size={16} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find a run by title, scenario or ID"
            aria-label="Search recovery runs"
          />
          {query && (
            <button
              className="icon-button"
              onClick={() => setQuery("")}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <div className="runs-toolbar">
          <div className="filter-tabs" aria-label="Filter recovery runs">
            {["all", "recovered", "blocked", "failed", "running"].map(
              (status) => (
                <button
                  key={status}
                  aria-pressed={filter === status}
                  className={filter === status ? "active" : ""}
                  onClick={() => setFilter(status)}
                >
                  {status === "all"
                    ? "All runs"
                    : status === "running"
                      ? "In progress"
                      : status}
                  <span>
                    {
                      runs.filter(
                        (r) => status === "all" || r.status === status,
                      ).length
                    }
                  </span>
                </button>
              ),
            )}
          </div>
          <button
            className="icon-button"
            aria-label="Refresh runs"
            onClick={onRefresh}
            disabled={refreshing}
          >
            <RefreshCw size={17} className={refreshing ? "spin" : ""} />
          </button>
        </div>
        {visible.length ? (
          <div className="run-table">
            <div className="run-table-head">
              <span>RECOVERY</span>
              <span>OUTCOME</span>
              <span>STARTED</span>
              <span>DURATION</span>
              <span />
            </div>
            {visible.map((run) => (
              <button
                className="run-table-row"
                onClick={() => onRun(run)}
                key={run.id}
              >
                <span className="table-run-title">
                  <span className="run-icon">
                    <Waypoints size={18} />
                  </span>
                  <span>
                    <strong>{run.title}</strong>
                    <small className="mono">
                      {short(run.id)} / {run.scenario}
                    </small>
                  </span>
                </span>
                <span>
                  <Status value={run.status} compact />
                </span>
                <span>{date(run.createdAt)}</span>
                <span className="mono">
                  {duration(run.metrics?.durationMs)}
                </span>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>
        ) : (
          <div className="large-empty">
            <span className="empty-orbit">
              <Waypoints size={36} />
            </span>
            <h2>
              {runs.length
                ? "No recoveries match."
                : "Nothing to recover. Yet."}
            </h2>
            <p>
              {runs.length
                ? "Try another title or scenario, or clear the filters to see your complete history."
                : "Your workspace starts with a clean slate. Introduce a controlled fault to see a real recovery, from detection through governance."}
            </p>
            <Button
              onClick={
                runs.length
                  ? () => {
                      setFilter("all");
                      setQuery("");
                    }
                  : onStart
              }
              className="button-primary"
            >
              {runs.length
                ? "Clear search and filters"
                : "Create your first recovery"}
              <ArrowRight size={16} />
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
function RunDetail({
  run,
  onBack,
  onStart,
  onError,
}: {
  run: Run;
  onBack: () => void;
  onStart: () => void;
  onError: (e: string) => void;
}) {
  const [tab, setTab] = useState<"activity" | "diff" | "evidence">("activity");
  const [stageFilter, setStageFilter] = useState<string | null>(null);
  const [artifactBusy, setArtifactBusy] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    name: string;
    content: string;
  } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const isRunning = run.status === "running";
  async function download() {
    setDownloading(true);
    try {
      const response = await fetch(
        `/api/runs/${encodeURIComponent(run.id)}/evidence`,
        { credentials: "same-origin" },
      );
      if (!response.ok)
        throw new Error("Evidence could not be downloaded. Please try again.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `aftercare-evidence-${run.id}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  }
  async function inspectArtifact(artifact: Artifact, downloadOnly = false) {
    if (!artifact.url?.startsWith(`/api/runs/${run.id}/artifacts/`)) return;
    setArtifactBusy(artifact.name);
    try {
      const response = await fetch(artifact.url, {
        credentials: "same-origin",
        headers: { Accept: downloadOnly ? "*/*" : "application/json" },
      });
      if (!response.ok) {
        if (response.status === 401)
          window.dispatchEvent(new Event("aftercare:session-ended"));
        throw new Error(
          "The artifact could not be loaded. Refresh the run and try again.",
        );
      }
      const blob = await response.blob();
      if (downloadOnly) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = artifact.name;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      } else {
        const text = await blob.text();
        let content = text;
        try {
          content = JSON.stringify(JSON.parse(text), null, 2);
        } catch {
          /* Preserve plain text artifacts. */
        }
        setPreview({ name: artifact.name, content });
      }
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setArtifactBusy(null);
    }
  }
  async function copyHash(artifact: Artifact) {
    try {
      await navigator.clipboard.writeText(artifact.sha256);
      setCopied(artifact.name);
      setTimeout(() => setCopied(null), 2500);
    } catch {
      onError(
        "Clipboard access is unavailable. Select the fingerprint in the evidence panel to copy it.",
      );
    }
  }
  function tabKey(event: React.KeyboardEvent<HTMLButtonElement>) {
    const names = ["activity", "diff", "evidence"] as const;
    const index = names.indexOf(tab);
    const key = event.key;
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(key)) return;
    event.preventDefault();
    const next =
      key === "Home"
        ? 0
        : key === "End"
          ? names.length - 1
          : (index + (key === "ArrowRight" ? 1 : -1) + names.length) %
            names.length;
    setTab(names[next]);
    event.currentTarget.parentElement
      ?.querySelectorAll<HTMLButtonElement>('[role="tab"]')
      [next]?.focus();
  }
  const stages = run.stages || [];
  const events = run.events || [];
  const artifacts = run.artifacts || [];
  const complete = stages.filter((s) => s.status === "passed").length;
  const selectedStage = stages.find((stage) => stage.id === stageFilter);
  const filteredEvents = stageFilter
    ? events.filter((event) => event.stage === stageFilter)
    : events;
  const recoveryEvent = events.find((e) => /ledger reconciled/i.test(e.title));
  const ledger =
    recoveryEvent?.evidence && typeof recoveryEvent.evidence === "object"
      ? (recoveryEvent.evidence as Record<string, unknown>)
      : null;
  return (
    <>
      <button className="back-link" onClick={onBack}>
        <ArrowLeft size={14} />
        All recovery runs
      </button>
      <div className="run-heading">
        <div>
          <div className="eyebrow">
            RECOVERY / <span className="mono">{short(run.id)}</span>
            <span className="eyebrow-separator">/</span> ISOLATED SANDBOX
          </div>
          <h1>{run.title}</h1>
          <p>
            Started {date(run.createdAt)}
            <span>·</span>
            <GitBranch size={13} /> {run.scenario}
          </p>
        </div>
        <div className="run-heading-actions">
          <Status value={run.status} />
          <Button onClick={download} disabled={downloading || isRunning}>
            <ArrowDownToLine size={15} />
            {isRunning
              ? "Evidence pending"
              : downloading
                ? "Exporting…"
                : "Export evidence"}
          </Button>
        </div>
      </div>
      <div className={`decision-banner decision-${run.status}`}>
        <span className="decision-icon">
          {isRunning ? (
            <Radar size={25} className="pulse" />
          ) : run.status === "recovered" ? (
            <ShieldCheck size={25} />
          ) : (
            <Shield size={25} />
          )}
        </span>
        <div>
          <strong>
            {isRunning
              ? "The recovery loop is working."
              : run.status === "recovered"
                ? "The customer promise is restored."
                : run.status === "blocked"
                  ? "The boundary held. This repair was blocked."
                  : "Recovery needs attention."}
          </strong>
          <p>
            {run.decision?.reason ||
              (isRunning
                ? "Executing real sandbox checks. Evidence appears below as each step finishes."
                : "Inspect the event evidence for the final outcome.")}
          </p>
        </div>
        <span className="decision-progress mono">{complete} / 9 stages</span>
      </div>
      <div className="stage-track" aria-label="Lifecycle stage execution">
        {stageNames.map((id, i) => {
          const stage = stages.find((s) => s.id === id);
          return (
            <button
              type="button"
              aria-pressed={stageFilter === id}
              aria-label={`${id}: ${stage?.status || "pending"}. Inspect stage activity`}
              title={stage?.detail || "Waiting to execute"}
              key={id}
              onClick={() => {
                setStageFilter(stageFilter === id ? null : id);
                setTab("activity");
              }}
              className={`stage-step stage-${stage?.status || "pending"} ${stageFilter === id ? "stage-selected" : ""}`}
            >
              <span className="stage-marker">
                {stage?.status === "passed" ? (
                  <Check size={12} />
                ) : stage?.status === "running" ? (
                  <LoaderCircle size={12} className="spin" />
                ) : stage?.status === "blocked" ||
                  stage?.status === "failed" ? (
                  <X size={12} />
                ) : (
                  <span>{i + 1}</span>
                )}
              </span>
              <strong>{id}</strong>
              <small>{stage?.status || "pending"}</small>
            </button>
          );
        })}
      </div>
      {stageFilter && (
        <div className="stage-insight">
          <div>
            <span className="eyebrow">{stageFilter} / STAGE EVIDENCE</span>
            <strong>
              {selectedStage?.detail || "This stage is waiting to execute."}
            </strong>
          </div>
          <button className="text-link" onClick={() => setStageFilter(null)}>
            Show all activity
            <X size={13} />
          </button>
        </div>
      )}
      <div className="run-detail-grid">
        <div className="run-detail-main">
          <section className="panel outcome-panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">THE OUTCOME THAT MATTERS</span>
                <h2>Health ≠ customer safety</h2>
              </div>
              <HeartPulse size={20} />
            </div>
            <div className="comparison">
              <div className="comparison-labels">
                <span>RELEASE SIGNAL</span>
                <span>Service health</span>
                <span>Customer promise</span>
                <span>Revision</span>
              </div>
              <div>
                <span className="comparison-caption">BEFORE RECOVERY</span>
                <span className="health-value">
                  <span className="signal-dot" />
                  {run.before?.healthStatus || "Pending"}
                </span>
                <span className="invariant-value before-value">
                  {run.before?.contractStatus || "Pending"}
                </span>
                <span className="mono">{short(run.before?.revision)}</span>
              </div>
              <ArrowRight className="comparison-arrow" size={18} />
              <div>
                <span className="comparison-caption">
                  {isRunning ? "RECOVERY IN PROGRESS" : "AFTER RECOVERY"}
                </span>
                <span className="health-value">
                  <span
                    className={`signal-dot ${!run.after?.healthStatus ? "signal-muted" : ""}`}
                  />
                  {run.after?.healthStatus || "Awaiting proof"}
                </span>
                <span
                  className={`invariant-value ${run.status === "recovered" ? "after-value" : ""}`}
                >
                  {run.after?.contractStatus || "Awaiting proof"}
                </span>
                <span className="mono">{short(run.after?.revision)}</span>
              </div>
            </div>
            {recoveryEvent && (
              <div className="reconciliation-note">
                <CheckCheck size={18} />
                <div>
                  <strong>{recoveryEvent.title}</strong>
                  <p>{recoveryEvent.detail}</p>
                  {ledger && (
                    <div className="ledger-facts">
                      <span>
                        <strong>
                          {String(ledger.syntheticDebits ?? "Not yet")}
                        </strong>{" "}
                        original debits
                      </span>
                      <span>
                        <strong>{String(ledger.reversals ?? "Not yet")}</strong>{" "}
                        append-only reversals
                      </span>
                      <span>
                        <strong>
                          {String(ledger.netTestCredits ?? "Not yet")}
                        </strong>{" "}
                        net test credits
                      </span>
                    </div>
                  )}
                </div>
                <span className="mono">SYNTHETIC LEDGER</span>
              </div>
            )}
          </section>
          <section className="panel activity-panel">
            <div
              className="detail-tabs"
              role="tablist"
              aria-label="Run details"
            >
              {[
                {
                  id: "activity",
                  label: "Live activity",
                  icon: Activity,
                  count: events.length,
                },
                { id: "diff", label: "Repair diff", icon: Code2 },
                {
                  id: "evidence",
                  label: "Evidence",
                  icon: Fingerprint,
                  count: artifacts.length,
                },
              ].map((item) => (
                <button
                  role="tab"
                  id={`run-${run.id}-tab-${item.id}`}
                  aria-controls={`run-${run.id}-panel-${item.id}`}
                  tabIndex={tab === item.id ? 0 : -1}
                  onKeyDown={tabKey}
                  aria-selected={tab === item.id}
                  key={item.id}
                  onClick={() => setTab(item.id as typeof tab)}
                  className={tab === item.id ? "active" : ""}
                >
                  <item.icon size={15} />
                  {item.label}
                  {item.count !== undefined && <span>{item.count}</span>}
                </button>
              ))}
              {isRunning && (
                <span className="live-label">
                  <span className="live-dot" />
                  LIVE
                </span>
              )}
            </div>
            <div
              role="tabpanel"
              id={`run-${run.id}-panel-${tab}`}
              aria-labelledby={`run-${run.id}-tab-${tab}`}
              tabIndex={0}
            >
              {tab === "activity" && (
                <div className="event-timeline">
                  {!filteredEvents.length && (
                    <div className="waiting-events">
                      {isRunning ? (
                        <LoaderCircle className="spin" size={20} />
                      ) : (
                        <FileCheck2 size={20} />
                      )}{" "}
                      {stageFilter
                        ? selectedStage?.detail ||
                          "No events were recorded for this stage."
                        : isRunning
                          ? "Waiting for the first execution event…"
                          : "No events were recorded for this run."}
                    </div>
                  )}
                  {filteredEvents.map((event, i) => (
                    <div className={`event event-${event.kind}`} key={event.id}>
                      <div className="event-rail">
                        <span>
                          {event.kind === "success" ? (
                            <Check size={12} />
                          ) : event.kind === "error" ||
                            event.kind === "warning" ? (
                            <Shield size={12} />
                          ) : (
                            <Circle size={9} />
                          )}
                        </span>
                        {i < filteredEvents.length - 1 && <i />}
                      </div>
                      <div className="event-body">
                        <button
                          className="event-heading"
                          onClick={() =>
                            setExpanded(expanded === event.id ? null : event.id)
                          }
                          aria-controls={`event-${event.id}`}
                          aria-expanded={expanded === event.id}
                        >
                          <span>
                            <span className="event-stage">{event.stage}</span>
                            <strong>
                              {event.title.replaceAll("\u2014", ", ")}
                            </strong>
                          </span>
                          <span className="event-time mono">
                            {new Date(event.at).toLocaleTimeString(undefined, {
                              hour12: false,
                            })}
                            <ChevronDown
                              size={13}
                              className={expanded === event.id ? "rotated" : ""}
                            />
                          </span>
                        </button>
                        <p>{event.detail.replaceAll("\u2014", ", ")}</p>
                        {expanded === event.id && (
                          <div
                            id={`event-${event.id}`}
                            className="event-evidence"
                          >
                            <div>
                              <Fingerprint size={13} />
                              <strong>HASH-LINKED EVENT</strong>
                              <span className="mono">
                                {event.hash || "Pending hash"}
                              </span>
                            </div>
                            <div className="event-previous-hash">
                              <span>Previous event hash</span>
                              <code>
                                {event.previousHash || "Chain origin"}
                              </code>
                            </div>
                            <pre>
                              {JSON.stringify(
                                event.evidence ?? {
                                  stage: event.stage,
                                  title: event.title,
                                  detail: event.detail,
                                  previousHash: event.previousHash,
                                },
                                null,
                                2,
                              )}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {isRunning && (
                    <div className="timeline-running">
                      <LoaderCircle size={14} className="spin" />
                      <span>Executing {run.stage || "recovery"}…</span>
                    </div>
                  )}
                </div>
              )}
              {tab === "diff" && (
                <div className="diff-inspector">
                  {run.diff?.path ? (
                    <>
                      <div className="diff-file">
                        <Code2 size={15} />
                        <span className="mono">{run.diff.path}</span>
                        <span>Observed repair</span>
                      </div>
                      <div className="diff-columns">
                        <div>
                          <div className="diff-label">BEFORE</div>
                          <pre>{run.diff.before || "(empty file)"}</pre>
                        </div>
                        <div>
                          <div className="diff-label">AFTER</div>
                          <pre>{run.diff.after || "(awaiting repair)"}</pre>
                        </div>
                      </div>
                      <div className="diff-note">
                        <ShieldCheck size={15} /> Repair scope is evaluated
                        against policy before a release can proceed.
                      </div>
                    </>
                  ) : (
                    <div className="tab-empty">
                      <Code2 size={28} />
                      <h3>No repair diff yet.</h3>
                      <p>
                        {isRunning
                          ? "The controller will publish the proposed code change as execution progresses."
                          : "No eligible code change was produced by this run."}
                      </p>
                    </div>
                  )}
                </div>
              )}
              {tab === "evidence" && (
                <div className="artifact-inspector">
                  <div className="evidence-intro">
                    <Fingerprint size={26} />
                    <div>
                      <h3>Evidence you can take with you.</h3>
                      <p>
                        Actual execution artifacts with SHA-256 fingerprints.
                        Export the complete record to inspect its hash chain
                        independently.
                      </p>
                    </div>
                  </div>
                  {artifacts.length ? (
                    artifacts.map((artifact, i) => (
                      <div
                        className="artifact-row"
                        key={`${artifact.name}-${i}`}
                      >
                        <span className="artifact-icon">
                          <FileJson size={20} />
                        </span>
                        <div>
                          <strong>{artifact.name}</strong>
                          <span>
                            {(
                              {
                                "release-bundle": "Immutable release bundle",
                                sbom: "Component manifest",
                                "synthetic-ledger": "Customer-impact ledger",
                              } as Record<string, string>
                            )[artifact.type] || artifact.type}
                          </span>
                          <code title={artifact.sha256}>
                            SHA256 {artifact.sha256}
                          </code>
                        </div>
                        <div className="artifact-actions">
                          <button
                            className="icon-button"
                            title="Copy fingerprint"
                            aria-label={`Copy fingerprint for ${artifact.name}`}
                            onClick={() => void copyHash(artifact)}
                          >
                            {copied === artifact.name ? (
                              <Check size={16} />
                            ) : (
                              <Fingerprint size={16} />
                            )}
                          </button>
                          {artifact.url?.startsWith(
                            `/api/runs/${run.id}/artifacts/`,
                          ) && (
                            <>
                              {artifact.name.endsWith(".json") && (
                                <button
                                  className="icon-button"
                                  title="Preview JSON"
                                  aria-label={`Preview ${artifact.name}`}
                                  disabled={artifactBusy === artifact.name}
                                  onClick={() => void inspectArtifact(artifact)}
                                >
                                  <Eye size={16} />
                                </button>
                              )}
                              <button
                                className="artifact-download icon-button"
                                title="Download artifact"
                                aria-label={`Download ${artifact.name}`}
                                disabled={artifactBusy === artifact.name}
                                onClick={() =>
                                  void inspectArtifact(artifact, true)
                                }
                              >
                                {artifactBusy === artifact.name ? (
                                  <LoaderCircle size={16} className="spin" />
                                ) : (
                                  <ArrowDownToLine size={16} />
                                )}
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="tab-empty">
                      <FileJson size={24} />
                      <p>Artifacts appear as the recovery stages execute.</p>
                    </div>
                  )}
                  <div className="artifact-copy-status" role="status">
                    {copied
                      ? "Fingerprint copied to clipboard."
                      : "Preview JSON, copy a fingerprint or download an artifact."}
                  </div>
                  <Button
                    onClick={download}
                    disabled={downloading || isRunning}
                  >
                    <ArrowDownToLine size={15} />
                    {isRunning
                      ? "Evidence available when complete"
                      : downloading
                        ? "Exporting evidence…"
                        : "Export complete evidence"}
                  </Button>
                </div>
              )}
            </div>
          </section>
        </div>
        <aside className="run-detail-aside">
          <section className="panel run-summary">
            <div className="panel-heading">
              <span className="eyebrow">EXECUTION FACTS</span>
              <Terminal size={16} />
            </div>
            <dl>
              {[
                {
                  label: isRunning ? "Elapsed" : "Duration",
                  value: duration(
                    isRunning
                      ? Math.max(
                          run.metrics?.durationMs || 0,
                          Date.now() - new Date(run.createdAt).getTime(),
                        )
                      : run.metrics?.durationMs,
                  ),
                },
                {
                  label: "Tests passing",
                  value: `${run.metrics?.testsPassed || 0} / ${run.metrics?.testsTotal || 0}`,
                },
                {
                  label: "Requests replayed",
                  value: run.metrics?.requestsReplayed ?? "Not yet",
                },
                {
                  label: "Extra debits observed",
                  value: run.metrics?.duplicateCharges ?? "Not yet",
                },
                {
                  label: "Model calls",
                  value: run.metrics?.modelCalls ?? "Not yet",
                },
                {
                  label: "Artifacts reused",
                  value: run.metrics?.artifactsReused ?? "Not yet",
                },
              ].map((fact) => (
                <div key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd className="mono">{fact.value}</dd>
                </div>
              ))}
            </dl>
            <p className="summary-note">
              Figures come from this execution. Reference mode uses
              deterministic repairs and makes no model calls.
            </p>
          </section>
          <section className="panel boundary-card">
            <ShieldCheck size={21} />
            <span className="eyebrow">AUTONOMY, BOUNDED</span>
            <h3>
              Hands off.
              <br />
              Rules on.
            </h3>
            <p>
              Each repair must clear the same policy gates. An unsafe candidate
              is blocked, even when health checks pass.
            </p>
            <div>
              <LockKeyhole size={13} /> Isolated execution scope
            </div>
            <div>
              <FileCheck2 size={13} /> Append-only event evidence
            </div>
            <div>
              <GitBranch size={13} /> Explicit repair boundaries
            </div>
          </section>
          {run.integrations &&
            Object.values(run.integrations).some(Boolean) && (
              <section className="panel integration-links">
                <span className="eyebrow">LINKED GITLAB EVIDENCE</span>
                {Object.entries(run.integrations)
                  .filter(([, url]) => /^https:\/\//.test(url || ""))
                  .map(([name, url]) => (
                    <a
                      href={url}
                      key={name}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {name
                        .replace("Url", "")
                        .replace("mr", "Merge request")
                        .replace("issue", "Issue")
                        .replace("pipeline", "Pipeline")}
                      <ExternalLink size={13} />
                    </a>
                  ))}
              </section>
            )}
          <button className="next-run" onClick={onStart}>
            <Plus size={17} />
            <span>Test another promise</span>
            <ArrowRight size={15} />
          </button>
        </aside>
      </div>
      {preview && (
        <Modal title={preview.name} onClose={() => setPreview(null)} wide>
          <p className="muted">
            Read-only artifact content from this recovery run.
          </p>
          <pre className="artifact-preview">{preview.content}</pre>
        </Modal>
      )}
    </>
  );
}
function PromisesPage({
  contracts,
  onStart,
}: {
  contracts: Contract[];
  onStart: () => void;
}) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <>
      <PageHeading
        eyebrow="CUSTOMER CONTRACTS"
        title="What a green check can’t tell you."
        description="Executable promises turn customer harm into something a release can detect and repair."
        action={
          <Button className="button-primary" onClick={onStart}>
            <Play size={14} />
            Test a promise
          </Button>
        }
      />
      <div className="promise-intro">
        <span className="big-quote">“</span>
        <p>
          My order was charged once.
          <br />
          My data stayed in my workspace.
          <br />
          <em>The recovery didn’t make things worse.</em>
        </p>
        <span className="eyebrow">THE CUSTOMER’S DEFINITION OF DONE</span>
      </div>
      <div className="contract-grid">
        {contracts.map((contract, i) => (
          <section className="panel contract-card" key={contract.id}>
            <div className="contract-card-top">
              <span className="promise-number">0{i + 1}</span>
              <span className="contract-category">{contract.category}</span>
              <ShieldCheck size={18} />
            </div>
            <h2>{contract.name}</h2>
            <p>{contract.description}</p>
            <div className="contract-source">
              <Code2 size={14} />
              <span className="mono">{contract.source}</span>
            </div>
            <button
              className="contract-details-button"
              aria-expanded={open === contract.id}
              onClick={() => setOpen(open === contract.id ? null : contract.id)}
            >
              {open === contract.id
                ? "Hide contract details"
                : "Inspect contract details"}
              <ChevronDown
                size={15}
                className={open === contract.id ? "rotated" : ""}
              />
            </button>
            {open === contract.id && (
              <div className="contract-expanded">
                <dl>
                  <div>
                    <dt>Contract ID</dt>
                    <dd className="mono">{contract.id}</dd>
                  </div>
                  <div>
                    <dt>Definition status</dt>
                    <dd>{contract.status}</dd>
                  </div>
                  <div>
                    <dt>Evaluation</dt>
                    <dd>Per recovery execution</dd>
                  </div>
                </dl>
                <p>
                  A registered contract is a definition. Inspect a recovery run
                  for measured before-and-after results.
                </p>
                <Button onClick={onStart}>
                  Run a scenario
                  <ArrowRight size={14} />
                </Button>
              </div>
            )}
          </section>
        ))}
      </div>
      <div className="promise-bottom-note">
        <BookOpen size={22} />
        <div>
          <h3>Promises are executable, not aspirational.</h3>
          <p>
            The sandbox evaluates these contracts against an intentionally
            faulty revision and the proposed recovery. Every verdict belongs to
            an individual run; a contract definition alone is no claim that a
            live system is safe.
          </p>
        </div>
      </div>
    </>
  );
}
function PolicyPage({
  data,
  onHelp,
  onGitLab,
}: {
  data: Overview;
  onHelp: () => void;
  onGitLab: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const connected =
    data.integration.mode === "gitlab" && data.integration.gitlabConfigured;
  return (
    <>
      <PageHeading
        eyebrow="GOVERNANCE & EXECUTION"
        title="Trust is a boundary, not a button."
        description="Autonomy is useful when the rules are explicit and the evidence is inspectable."
      />
      <div className="policy-grid">
        <section className="panel policy-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">ENFORCED CONTROLLER POLICY</span>
              <h2>Hands off. Within limits.</h2>
            </div>
            <ShieldCheck size={23} />
          </div>
          <div className="policy-row">
            <div>
              <strong>Autonomy level</strong>
              <p>The controller clears its own gates inside the sandbox.</p>
            </div>
            <span className="policy-value">{data.policy.autonomy}</span>
          </div>
          <div className="policy-row">
            <div>
              <strong>Repair attempt ceiling</strong>
              <p>A finite budget keeps recovery from becoming a loop.</p>
            </div>
            <span className="policy-value mono">
              {data.policy.maxAttempts} attempts
            </span>
          </div>
          <div className="policy-paths">
            <div>
              <strong>Allowed repair paths</strong>
              <p>Changes outside this scope must stop at the policy gate.</p>
            </div>
            {data.policy.allowedPaths?.length ? (
              data.policy.allowedPaths.map((path) => (
                <code key={path}>
                  <LockKeyhole size={13} />
                  {path}
                </code>
              ))
            ) : (
              <span className="muted">
                See the raw policy for configured boundaries.
              </span>
            )}
          </div>
          <button
            className="contract-details-button"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            Inspect raw controller policy
            <ChevronDown size={15} className={expanded ? "rotated" : ""} />
          </button>
          {expanded && (
            <pre className="raw-policy">
              {JSON.stringify(data.policy, null, 2)}
            </pre>
          )}
          <div className="read-only-note">
            <LockKeyhole size={14} /> Policy is managed in source control. This
            view reflects the active controller configuration.
          </div>
        </section>
        <div>
          <section className="panel connection-card">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">EXECUTION CONNECTION</span>
                <h2>
                  {connected ? "GitLab configured" : "Reference controller"}
                </h2>
              </div>
              <Waypoints size={22} />
            </div>
            <Status value={connected ? "connected" : "sandbox"} />
            <p>
              {connected
                ? "A GitLab configuration is available. Inspect each recovery’s linked issue, merge request and pipeline evidence to confirm what executed."
                : "The reference controller executes real recovery checks in an isolated sandbox using deterministic repairs. Source repair runs separately in GitLab Duo. Inspect the live workflow for its actual session and pipeline evidence."}
            </p>
            <div className="connection-facts">
              <div>
                <span>Execution scope</span>
                <strong>Isolated sandbox</strong>
              </div>
              <div>
                <span>Run integration</span>
                <strong>
                  {data.integration.gitlabConfigured
                    ? "GitLab available"
                    : "Reference only"}
                </strong>
              </div>
              <div>
                <span>Mode reported by API</span>
                <code>{data.integration.mode}</code>
              </div>
            </div>
            <Button onClick={onHelp}>
              Understand connection modes
              <ArrowRight size={14} />
            </Button>
            <Button onClick={onGitLab} className="workflow-policy-link">
              <GitBranch size={14} />
              Inspect live GitLab workflow
              <ArrowRight size={14} />
            </Button>
          </section>
          <section className="policy-principle">
            <Fingerprint size={28} />
            <h3>Proof over permission.</h3>
            <p>
              A green button is not evidence. Every recovery carries its
              verdicts, artifacts, diff, and hash-linked event record.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}
function GitLabWorkflowPage() {
  const [evidence, setEvidence] = useState<GitLabEvidence | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = async () => {
    setBusy(true);
    setError("");
    try {
      setEvidence(await api<GitLabEvidence>("/api/gitlab/evidence"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const external = (url?: string) => !!url && /^https:\/\//.test(url);
  return (
    <>
      <PageHeading
        eyebrow="LIVE SOURCE EVIDENCE / GITLAB"
        title="The repair has a paper trail."
        description="Follow the issue, the Duo session, the proposed change, and its actual CI results."
        action={
          <Button onClick={load} disabled={busy}>
            <RefreshCw size={15} className={busy ? "spin" : ""} />
            {busy ? "Checking GitLab…" : "Refresh evidence"}
          </Button>
        }
      />
      <div className="workflow-context">
        <span className="workflow-context-icon">
          <GitBranch size={23} />
        </span>
        <div>
          <strong>Two execution paths. One customer promise.</strong>
          <p>
            The sandbox runs the deterministic reference controller. This page
            independently reads the project’s GitLab workflow evidence: agent
            source edits, merge requests and pipelines. A passing sandbox run
            does not imply a completed Duo session.
          </p>
        </div>
        <span className="workflow-readonly">
          <LockKeyhole size={11} />
          READ ONLY
        </span>
      </div>
      {error && <ErrorNotice error={error} />}
      {!evidence && busy ? (
        <section className="panel workflow-loading">
          <LoaderCircle size={25} className="spin" />
          <h3>Reading the project’s execution evidence.</h3>
          <p>Fetching pipeline and merge request metadata from GitLab.</p>
        </section>
      ) : !evidence ? (
        <section className="panel workflow-unavailable">
          <Globe2 size={30} />
          <h2>GitLab evidence is unavailable.</h2>
          <p>
            The project could not be checked right now. Refresh to retry; no
            execution status has been assumed.
          </p>
          <Button onClick={load} disabled={busy}>
            <RefreshCw size={14} />
            Try again
          </Button>
        </section>
      ) : (
        <>
          <div
            className={`workflow-check ${!evidence.available || evidence.stale ? "workflow-check-warning" : ""}`}
          >
            <div>
              <span className="live-dot" />
              <strong>
                {evidence.stale
                  ? "Previously fetched evidence"
                  : evidence.available
                    ? "Project evidence available"
                    : "GitLab check unavailable"}
              </strong>
              {evidence.checkedAt && (
                <span>Checked {date(evidence.checkedAt)}</span>
              )}
            </div>
            <p>{evidence.detail}</p>
            {external(evidence.projectUrl) && (
              <a
                href={evidence.projectUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open public project
                <ExternalLink size={13} />
              </a>
            )}
          </div>
          <section
            className="workflow-sequence"
            aria-label="GitLab recovery workflow"
          >
            <div className="workflow-sequence-card">
              <span className="workflow-step-number">01 / INTENT</span>
              <span className="workflow-step-icon">
                <BookOpen size={20} />
              </span>
              <h2>Start with the incident.</h2>
              <p>
                The issue captures the broken promise and a scoped recovery
                intent. It is the source of the workflow’s task.
              </p>
              {external(evidence.issueUrl) ? (
                <a
                  className="workflow-source-link"
                  href={evidence.issueUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open incident issue
                  <ExternalLink size={13} />
                </a>
              ) : (
                <span className="workflow-link-unavailable">
                  Issue link unavailable
                </span>
              )}
            </div>
            <div className="workflow-sequence-card">
              <span className="workflow-step-number">02 / AGENT</span>
              <span className="workflow-step-icon">
                <Sparkles size={20} />
              </span>
              <h2>Let Duo work in source.</h2>
              <p>
                The custom flow supplies diagnosis and bounded repair
                instructions. Open the session to inspect its actual execution
                and messages.
              </p>
              <div className="workflow-agent-links">
                {external(evidence.flowUrl) && (
                  <a
                    className="workflow-source-link"
                    href={evidence.flowUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open custom flow
                    <ExternalLink size={13} />
                  </a>
                )}
                {external(evidence.sessionUrl) ? (
                  <a
                    className="workflow-source-link"
                    href={evidence.sessionUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open Duo session
                    <ExternalLink size={13} />
                  </a>
                ) : (
                  <span className="workflow-link-unavailable">
                    Session link unavailable
                  </span>
                )}
              </div>
              <span className="workflow-verification-note">
                A session link is not a completion verdict.
              </span>
            </div>
            <div className="workflow-sequence-card">
              <span className="workflow-step-number">03 / PROOF</span>
              <span className="workflow-step-icon">
                <FileCheck2 size={20} />
              </span>
              <h2>Judge the change.</h2>
              <p>
                Read the actual proposed diff, branch and commit. CI results
                below report what GitLab ran; they stay independent of sandbox
                outcomes.
              </p>
              <div className="workflow-proof-counts">
                <span>
                  <strong>{evidence.mergeRequests.length}</strong> merge
                  requests returned
                </span>
                <span>
                  <strong>{evidence.pipelines.length}</strong> pipelines
                  returned
                </span>
              </div>
            </div>
          </section>
          <div className="workflow-records">
            <section className="panel workflow-mrs">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">SOURCE CHANGES</span>
                  <h2>Repair proposals</h2>
                </div>
                <GitBranch size={20} />
              </div>
              {evidence.mergeRequests.length ? (
                <div className="workflow-record-list">
                  {evidence.mergeRequests.map((mr) => (
                    <div className="workflow-mr" key={mr.iid}>
                      <div className="workflow-record-title">
                        <span className="mono">!{mr.iid}</span>
                        <strong>{mr.title}</strong>
                        <Status value={mr.state} compact />
                      </div>
                      <div className="workflow-record-meta">
                        <GitBranch size={12} />
                        <code>{mr.sourceBranch}</code>
                        <span>·</span>
                        <code>{short(mr.sha)}</code>
                      </div>
                      {external(mr.url) && (
                        <a
                          className="workflow-source-link"
                          href={mr.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Inspect merge request
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="workflow-empty">
                  <GitBranch size={26} />
                  <h3>No merge request returned.</h3>
                  <p>
                    {evidence.available
                      ? "The API returned no merge request in this evidence snapshot. Refresh after the agent proposes a change."
                      : "Merge request state could not be retrieved. Open the project or retry the check."}
                  </p>
                </div>
              )}
            </section>
            <section className="panel workflow-pipelines">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">ACTUAL CI HISTORY</span>
                  <h2>Pipeline results</h2>
                </div>
                <Waypoints size={20} />
              </div>
              {evidence.pipelines.length ? (
                <div className="workflow-record-list">
                  {evidence.pipelines.map((pipeline) => (
                    <div className="workflow-pipeline" key={pipeline.id}>
                      <div className="workflow-record-title">
                        <span className="mono">#{pipeline.id}</span>
                        <Status value={pipeline.status} compact />
                        {external(pipeline.url) && (
                          <a
                            href={pipeline.url}
                            aria-label={`Open pipeline ${pipeline.id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                      </div>
                      <div className="workflow-record-meta">
                        <GitBranch size={12} />
                        <code>{pipeline.ref}</code>
                        <span>·</span>
                        <code>{short(pipeline.sha)}</code>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="workflow-empty">
                  <Waypoints size={26} />
                  <h3>No pipeline returned.</h3>
                  <p>
                    {evidence.available
                      ? "There is no pipeline in this evidence snapshot. An empty history is not a passing result."
                      : "Pipeline results could not be retrieved. No success is inferred."}
                  </p>
                </div>
              )}
            </section>
          </div>
          <div className="workflow-footnote">
            <Fingerprint size={19} />
            <p>
              <strong>Evidence has a scope.</strong> This view shows source
              project metadata fetched by the backend. Review linked job logs
              and the Duo session for implementation details. It does not claim
              that an external release or customer payment occurred.
            </p>
          </div>
        </>
      )}
    </>
  );
}
function HelpModal({
  onClose,
  connected,
}: {
  onClose: () => void;
  connected: boolean;
}) {
  return (
    <Modal title="A recovery loop you can inspect." onClose={onClose} wide>
      <p className="muted modal-description">
        Aftercare treats a broken customer promise as a release incident, then
        carries the fix through a bounded post-code workflow.
      </p>
      <div className="help-flow">
        {[
          {
            icon: Search,
            title: "Detect the harm",
            text: "Replay a customer contract against a faulty release. Service health and customer safety are evaluated separately.",
          },
          {
            icon: Code2,
            title: "Repair within bounds",
            text: "Build a scoped candidate, run real checks, and enforce the allowed paths before any release step.",
          },
          {
            icon: ShieldCheck,
            title: "Prove the outcome",
            text: "Validate the candidate, reconcile synthetic harm, and preserve the decision with downloadable evidence.",
          },
        ].map((item) => (
          <div key={item.title}>
            <span>
              <item.icon size={21} />
            </span>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
          </div>
        ))}
      </div>
      <div className="mode-comparison">
        <div className={!connected ? "mode-current" : ""}>
          <span className="eyebrow">
            {!connected ? "YOUR CURRENT MODE" : "SANDBOX OPTION"}
          </span>
          <h3>Reference controller</h3>
          <p>
            Deterministic diagnosis and repairs. Real isolated execution, tests,
            packaging and evidence. No model calls or external pipeline claims.
          </p>
        </div>
        <div className={connected ? "mode-current" : ""}>
          <span className="eyebrow">
            {connected ? "CONFIGURED CONNECTION" : "SUPERVISED WORKFLOW"}
          </span>
          <h3>GitLab Duo flow</h3>
          <p>
            GitLab Duo investigates and repairs source in a separate workflow.
            Inspect the actual session, merge request and pipeline results in
            GitLab workflow.
          </p>
        </div>
      </div>
      <div className="modal-footnote">
        <Fingerprint size={15} /> An event hash links the execution record; it
        does not prove an external system ran.
      </div>
    </Modal>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
