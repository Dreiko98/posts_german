import { useState, useEffect, useCallback, type FormEvent } from "react";
import {
  Lightbulb,
  FileText,
  SlidersHorizontal,
  Bell,
  LogOut,
  ArrowUpRight,
  Activity,
  X,
  ChevronDown,
  LoaderCircle,
} from "lucide-react";
import { api, setCsrf, ApiError } from "./api";
import type { Preferences, Catalog, Job, Notice } from "./types";
import { Modal, ErrorBox, Loading, CostEstimate, JobsPanel } from "./ui";
import { IdeasPage } from "./Ideas";
import { PublicationsPage, Editor } from "./Publications";
import { SettingsPage } from "./Settings";

export type Action = <T>(
  work: () => Promise<T>,
  success?: string,
) => Promise<T | undefined>;

function Login({ onLogin }: { onLogin: (username: string) => void }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      const data = await api<{ username: string; csrf: string }>(
        "/auth/login",
        "POST",
        { username: form.get("username"), password: form.get("password") },
      );
      setCsrf(data.csrf);
      onLogin(data.username);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-brand">
        <span className="wordmark">
          germa<span>·</span>
        </span>
        <span className="eyebrow">DATOS · IA · IDEAS</span>
      </div>
      <div className="login-content">
        <section className="login-intro">
          <span className="eyebrow">TU ESPACIO EDITORIAL</span>
          <h1>
            Ideas con criterio.
            <br />
            <span>Contenido con voz.</span>
          </h1>
          <p>
            De una intención a un artículo propio.
            <br />
            Con contexto, fuentes y tu última palabra.
          </p>
          <div className="login-footnote">
            <span className="status-dot" />
            Un espacio privado para crear y revisar.
          </div>
        </section>
        <form onSubmit={submit} className="login-form">
          <span className="eyebrow">BIENVENIDO</span>
          <h2>Entrar al estudio</h2>
          <p>Accede a tus ideas y publicaciones.</p>
          <label>
            Usuario
            <input
              name="username"
              autoComplete="username"
              required
              autoFocus
              maxLength={100}
            />
          </label>
          <label>
            Contraseña
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={200}
            />
          </label>
          {error && <ErrorBox message={error} />}
          <button className="primary" disabled={busy}>
            {busy ? (
              <LoaderCircle size={18} className="spin" />
            ) : (
              <>
                Entrar <ArrowUpRight size={18} />
              </>
            )}
          </button>
          <small>
            El primer usuario se crea desde el servidor.
            <br />
            Consulta el procedimiento de instalación.
          </small>
        </form>
      </div>
      <footer>
        Germán Mallo <span>UN LABORATORIO DE IDEAS PROPIAS</span>
      </footer>
    </main>
  );
}

export default function App() {
  const [user, setUser] = useState<string | null>(null),
    [loading, setLoading] = useState(true),
    [startupError, setStartupError] = useState(""),
    [view, setView] = useState(
      new URLSearchParams(location.search).get("view") || "ideas",
    ),
    [pubId, setPubId] = useState<string | null>(null);
  const [prefs, setPrefs] = useState<Preferences | null>(null),
    [cat, setCat] = useState<Catalog | null>(null),
    [jobs, setJobs] = useState<Job[]>([]),
    [notices, setNotices] = useState<Notice[]>([]),
    [panel, setPanel] = useState<"jobs" | "notices" | "model" | null>(null),
    [message, setMessage] = useState<{
      text: string;
      error: boolean;
      action?: string;
    } | null>(null),
    [refresh, setRefresh] = useState(0);
  const action: Action = useCallback(async (work, success) => {
    try {
      const result = await work();
      if (success) setMessage({ text: success, error: false });
      setRefresh((x) => x + 1);
      return result;
    } catch (e) {
      const err = e as ApiError;
      setMessage({ text: err.message, error: true, action: err.action });
      if (err.code === "sesion_requerida") setUser(null);
      return undefined;
    }
  }, []);
  const loadSession = useCallback(() => {
    setLoading(true);
    setStartupError("");
    return api<{ username: string; csrf: string }>("/auth/session")
      .then((s) => {
        setCsrf(s.csrf);
        setUser(s.username);
      })
      .catch((error: ApiError) => {
        if (error.code === "sesion_requerida") setUser(null);
        else setStartupError(error.message);
      })
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    void loadSession();
  }, [loadSession]);
  useEffect(() => {
    if (!user) return;
    Promise.all([api<Preferences>("/preferences"), api<Catalog>("/catalog")])
      .then(([p, c]) => {
        setPrefs(p);
        setCat(c);
        setStartupError("");
      })
      .catch((e: ApiError) => {
        if (e.code === "sesion_requerida") {
          setUser(null);
          setPrefs(null);
          setCat(null);
        } else {
          setStartupError(e.message);
          setMessage({ text: e.message, error: true });
        }
      });
  }, [user, refresh]);
  useEffect(() => {
    if (!user) return;
    let alive = true;
    let last: string | null = null;
    async function poll() {
      try {
        const [j, n] = await Promise.all([
          api<Job[]>("/jobs"),
          api<Notice[]>("/notifications"),
        ]);
        if (alive) {
          setJobs(j);
          setNotices(n);
          const signature = j.map((x) => x.id + x.state).join();
          if (last !== null && last !== signature) setRefresh((x) => x + 1);
          last = signature;
        }
      } catch {}
    }
    poll();
    const timer = setInterval(poll, 3000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [user]);
  useEffect(() => {
    if (!message || message.error) return;
    const t = setTimeout(() => setMessage(null), 5000);
    return () => clearTimeout(t);
  }, [message]);
  const openPub = (id: string) => {
    setPubId(id);
    setView("publicaciones");
  };
  async function changeModel(value: string) {
    const m = cat?.models.find((x) => x.provider + ":" + x.id === value);
    if (prefs && m)
      await action(
        () =>
          api("/preferences", "PUT", {
            ...prefs,
            provider: m.provider,
            model: m.id,
          }),
        "Modelo aplicado a las próximas operaciones.",
      );
  }
  if (loading) return <Loading />;
  if (startupError && (!user || !prefs || !cat))
    return (
      <main className="connection-failure">
        <span className="wordmark">
          germa<span>·</span>
        </span>
        <h1>No se pudo cargar el estudio</h1>
        <ErrorBox message={startupError} />
        <p>Puedes volver a intentarlo cuando el servicio esté disponible.</p>
        <button
          className="primary"
          onClick={() => {
            setStartupError("");
            if (user) setRefresh((value) => value + 1);
            else void loadSession();
          }}
        >
          Volver a intentar
        </button>
      </main>
    );
  if (!user) return <Login onLogin={setUser} />;
  if (!prefs || !cat) return <Loading />;
  const model = cat.models.find(
      (x) => x.provider === prefs.provider && x.id === prefs.model,
    ),
    active = jobs.filter((j) => ["pendiente", "ejecutando"].includes(j.state));
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#ideas"
          onClick={(e) => {
            e.preventDefault();
            setView("ideas");
            setPubId(null);
          }}
        >
          <span className="wordmark">
            germa<span>·</span>
          </span>
          <small>{prefs.app_name}</small>
        </a>
        <span className="nav-caption">ESPACIO EDITORIAL</span>
        <nav>
          {[
            { id: "ideas", label: "Ideas", icon: Lightbulb },
            { id: "publicaciones", label: "Publicaciones", icon: FileText },
            { id: "ajustes", label: "Ajustes", icon: SlidersHorizontal },
          ].map((item) => (
            <button
              className={view === item.id ? "nav-item active" : "nav-item"}
              key={item.id}
              onClick={() => {
                setView(item.id);
                setPubId(null);
              }}
            >
              <item.icon size={20} />
              {item.label}
              {view === item.id && <span className="nav-mark" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p>
            Tu voz.
            <br />
            <strong>Tu última palabra.</strong>
          </p>
          <button
            className="nav-item"
            onClick={() =>
              action(async () => {
                await api("/auth/logout", "POST");
                setUser(null);
              })
            }
          >
            <LogOut size={18} />
            Cerrar sesión
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="top-context">
            <span className="status-dot" />
            <span>Estudio privado</span>
          </div>
          <div className="top-actions">
            <label className="model-picker">
              <span>MODELO GENERAL</span>
              <select
                aria-label="Proveedor y modelo general"
                value={prefs.provider + ":" + prefs.model}
                onChange={(e) => changeModel(e.target.value)}
              >
                {cat.models.map((m) => (
                  <option
                    key={m.provider + ":" + m.id}
                    value={m.provider + ":" + m.id}
                  >
                    {m.provider === "openai" ? "OpenAI" : "Anthropic"} ·{" "}
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="icon-button"
              aria-label="Información y coste del modelo"
              onClick={() => setPanel("model")}
            >
              <ChevronDown size={18} />
            </button>
            <button
              className="icon-button"
              aria-label="Trabajos y progreso"
              onClick={() => setPanel("jobs")}
            >
              <Activity size={20} />
              {active.length > 0 && <span className="notification-dot" />}
            </button>
            <button
              className="icon-button"
              aria-label="Notificaciones"
              onClick={() => setPanel("notices")}
            >
              <Bell size={20} />
              {notices.some((n) => !n.read) && (
                <span className="notification-dot" />
              )}
            </button>
            <div className="avatar" title={user}>
              {user.slice(0, 1).toUpperCase()}
            </div>
          </div>
        </header>
        <main className="main-content">
          {view === "ideas" ? (
            <IdeasPage
              action={action}
              refresh={refresh}
              openPub={openPub}
              jobs={jobs}
            />
          ) : view === "publicaciones" ? (
            pubId ? (
              <Editor
                id={pubId}
                action={action}
                refresh={refresh}
                jobs={jobs}
                onBack={() => setPubId(null)}
              />
            ) : (
              <PublicationsPage
                action={action}
                refresh={refresh}
                openPub={openPub}
                jobs={jobs}
              />
            )
          ) : (
            <SettingsPage
              action={action}
              refresh={refresh}
              prefs={prefs}
              catalog={cat}
            />
          )}
        </main>
        <footer className="workspace-footer">
          <span>Germán Mallo · Content Studio</span>
          <span>CONTEXTO → CRITERIO → CONTENIDO</span>
        </footer>
      </div>
      {message && (
        <div
          className={message.error ? "toast error" : "toast"}
          role={message.error ? "alert" : "status"}
        >
          <div>
            {message.text}
            {message.action && <small>{message.action}</small>}
          </div>
          <button
            className="icon-button"
            aria-label="Cerrar aviso"
            onClick={() => setMessage(null)}
          >
            <X size={18} />
          </button>
        </div>
      )}
      {panel && (
        <Modal
          title={
            panel === "jobs"
              ? "Trabajos y progreso"
              : panel === "notices"
                ? "Notificaciones"
                : "Modelo y estimación"
          }
          onClose={() => setPanel(null)}
          wide
        >
          {panel === "jobs" ? (
            jobs.length ? (
              <JobsPanel
                jobs={jobs}
                onCancel={(id) =>
                  action(
                    () => api("/jobs/" + id + "/cancel", "POST"),
                    "Cancelación solicitada.",
                  )
                }
                onResume={(id) =>
                  action(
                    () => api("/jobs/" + id + "/resume", "POST"),
                    "Trabajo reanudado con su configuración original.",
                  )
                }
              />
            ) : (
              <p className="muted">
                Aún no hay operaciones. Los trabajos se conservan aunque cierres
                el navegador.
              </p>
            )
          ) : panel === "notices" ? (
            <>
              <button
                className="text-button"
                onClick={() => action(() => api("/notifications/read", "POST"))}
              >
                Marcar como leídas
              </button>
              {notices.length ? (
                notices.map((n) => (
                  <div className="notice" key={n.id}>
                    {n.message}
                    <BadgeRead read={n.read} />
                  </div>
                ))
              ) : (
                <p className="muted">No hay notificaciones.</p>
              )}
            </>
          ) : model ? (
            <div className="model-detail">
              <h3>{model.name}</h3>
              <p>{model.description}</p>
              <p>
                Conexión:{" "}
                {model.availability?.replaceAll("_", " ") || "no comprobada"} ·
                Búsqueda web:{" "}
                {model.web_search ? "compatible" : "no compatible"}
              </p>
              <p>
                Tarifas USD / millón de tokens: entrada{" "}
                {model.input ?? "desconocida"} · salida{" "}
                {model.output ?? "desconocida"} · caché{" "}
                {model.cached ?? "desconocida"}. Búsqueda:{" "}
                {model.search ?? "desconocida"} USD por uso.
              </p>
              <a href={model.source} target="_blank" rel="noreferrer">
                Fuente oficial · comprobada {model.verified}
                <ArrowUpRight size={15} />
              </a>
              <CostEstimate estimate={model.estimate || null} />
              <p className="muted">
                Límite por operación: {prefs.max_cost} USD. Saldo del proveedor
                desconocido; se consulta en su panel. Un cambio de modelo
                conserva la configuración de los trabajos activos.
              </p>
            </div>
          ) : null}
        </Modal>
      )}
    </div>
  );
}
function BadgeRead({ read }: { read: boolean }) {
  return <small>{read ? "Leída" : "Nueva"}</small>;
}
