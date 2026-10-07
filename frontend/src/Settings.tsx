import { useState, useEffect, type FormEvent } from "react";
import {
  Save,
  Plug,
  ArrowUpRight,
  RefreshCw,
  Upload,
  ShieldCheck,
  SlidersHorizontal,
  UserRound,
  Coins,
  Check,
  ExternalLink,
} from "lucide-react";
import { api, dateTime, dollars } from "./api";
import type {
  Preferences,
  Catalog,
  OwnerContext,
  Connection,
  Metrics,
  Costs,
  Model,
} from "./types";
import type { Action } from "./App";
import { Badge, Modal, Loading, CostEstimate } from "./ui";

const providerNames: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  wordpress: "WordPress + Yoast",
  linkedin: "LinkedIn personal",
  ga4: "Google Analytics 4",
  search_console: "Search Console",
};
const fields: Record<
  string,
  {
    config: [string, string, string][];
    secrets: [string, string, string][];
    note: string;
  }
> = {
  openai: {
    config: [],
    secrets: [["api_key", "Clave API", "password"]],
    note: "El saldo exacto no está disponible aquí. La app registra sus llamadas y costes; consulta la facturación en el panel de OpenAI.",
  },
  anthropic: {
    config: [],
    secrets: [["api_key", "Clave API", "password"]],
    note: "La búsqueda web debe estar habilitada en tu organización. El saldo es desconocido; consulta el panel del proveedor.",
  },
  wordpress: {
    config: [
      ["url", "URL HTTPS de la web", "url"],
      ["username", "Usuario WordPress", "text"],
    ],
    secrets: [["application_password", "Contraseña de aplicación", "password"]],
    note: "Instala German Studio Connector y Yoast SEO gratuito. La app envía borradores; la publicación final se hace en WordPress.",
  },
  linkedin: {
    config: [
      ["client_id", "Client ID", "text"],
      ["redirect_uri", "Callback OAuth", "url"],
    ],
    secrets: [["client_secret", "Client secret", "password"]],
    note: "Configura los productos Sign In with LinkedIn using OpenID Connect y Share on LinkedIn: openid, profile y w_member_social. Guarda y pulsa Autorizar LinkedIn.",
  },
  ga4: {
    config: [["property_id", "ID numérico de propiedad GA4", "text"]],
    secrets: [["service_account", "JSON de cuenta de servicio", "textarea"]],
    note: "Activa Google Analytics Data API y concede a la cuenta de servicio lectura sobre la propiedad. No se modifica la analítica.",
  },
  search_console: {
    config: [
      [
        "site_url",
        "Propiedad (sc-domain:germanmallo.com o URL exacta)",
        "text",
      ],
    ],
    secrets: [["service_account", "JSON de cuenta de servicio", "textarea"]],
    note: "Activa Search Console API y añade la cuenta de servicio a la propiedad. La API devuelve filas principales; se identifica su cobertura parcial.",
  },
};

export function SettingsPage({
  action,
  refresh,
  prefs,
  catalog,
}: {
  action: Action;
  refresh: number;
  prefs: Preferences;
  catalog: Catalog;
}) {
  const [tab, setTab] = useState("contexto"),
    [ctx, setCtx] = useState<OwnerContext | null>(null),
    [draft, setDraft] = useState<OwnerContext["body"] | null>(null),
    [connections, setConnections] = useState<Connection[]>([]),
    [editConnection, setEditConnection] = useState<Connection | null>(null),
    [metrics, setMetrics] = useState<Metrics | null>(null),
    [costs, setCosts] = useState<Costs | null>(null),
    [limits, setLimits] = useState(prefs),
    [catText, setCatText] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    Promise.all([
      api<OwnerContext>("/context"),
      api<Connection[]>("/connections"),
      api<Metrics>("/metrics"),
      api<Costs>("/costs"),
    ])
      .then(([c, cn, m, co]) => {
        setCtx(c);
        setDraft((d) => d || c.body);
        setConnections(cn);
        setMetrics(m);
        setCosts(co);
      })
      .catch((e) => action(() => Promise.reject(e)));
  }, [refresh]);
  useEffect(() => setLimits(prefs), [prefs]);
  useEffect(
    () =>
      setCatText(
        JSON.stringify(
          catalog.models.map(({ availability, estimate, ...rest }) => rest),
          null,
          2,
        ),
      ),
    [catalog],
  );
  async function saveContext(e: FormEvent) {
    e.preventDefault();
    if (!ctx || !draft) return;
    setBusy(true);
    const result = await action(
      () =>
        api<OwnerContext>("/context", "PUT", {
          body: draft,
          revision: ctx.revision,
        }),
      "Contexto actualizado para nuevas generaciones.",
    );
    if (result) {
      setCtx(result);
      setDraft(result.body);
    }
    setBusy(false);
  }
  async function importText(file: File) {
    const f = new FormData();
    f.append("file", file);
    const result = await action(
      () =>
        api<{ text: string; source: Record<string, unknown> }>(
          "/context/import",
          "POST",
          f,
        ),
      "Texto importado como referencia. Revisa y guarda el contexto.",
    );
    if (result)
      setDraft((d) =>
        d
          ? {
              ...d,
              style_examples: (d.style_examples + "\n\n" + result.text).slice(
                0,
                20000,
              ),
              references: [...d.references, result.source].slice(0, 30),
            }
          : d,
      );
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">03 / LO QUE DA SENTIDO AL CONTENIDO</span>
          <h1>
            Ajustes<span className="accent">.</span>
          </h1>
          <p>Tu contexto, tus conexiones y los límites de tu estudio.</p>
        </div>
        <span className="heading-note">
          TU PERFIL EVOLUCIONA.
          <br />
          EL CONTEXTO TAMBIÉN.
        </span>
      </div>
      <div className="settings-tabs">
        {[
          ["contexto", "Mi contexto", UserRound],
          ["conexiones", "Conexiones", Plug],
          ["generacion", "Generación y costes", Coins],
          ["cuenta", "Cuenta", ShieldCheck],
        ].map(([id, label, Icon]) => {
          const I = Icon as typeof UserRound;
          return (
            <button
              key={id as string}
              className={tab === id ? "active" : ""}
              onClick={() => setTab(id as string)}
            >
              <I size={17} />
              {label as string}
            </button>
          );
        })}
      </div>
      {tab === "contexto" ? (
        ctx && draft ? (
          <form className="settings-panel context-form" onSubmit={saveContext}>
            <div className="section-heading">
              <div>
                <h2>Un contenido que se parece a ti</h2>
                <p>
                  El perfil vigente prevalece sobre textos históricos. Las
                  generaciones conservan una copia del contexto utilizado.
                </p>
              </div>
              <button className="primary" disabled={busy}>
                <Save size={17} />
                Guardar contexto
              </button>
            </div>
            {(
              [
                [
                  "profile",
                  "Perfil actual",
                  "Trayectoria, conocimientos y lo que haces hoy.",
                ],
                [
                  "projects",
                  "Proyectos relevantes",
                  "Problemas, soluciones y aprendizajes que puedes contar.",
                ],
                [
                  "goals",
                  "Objetivos editoriales",
                  "Qué quieres aportar y mostrar.",
                ],
                [
                  "audience",
                  "Público",
                  "Para quién escribes y qué nivel necesita.",
                ],
                ["tone", "Tu voz", "Tono, ejemplos y preferencias."],
                [
                  "avoid",
                  "Aspectos a evitar",
                  "Límites editoriales y estructuras que no encajan.",
                ],
                [
                  "confirmed_facts",
                  "Hechos y experiencias confirmados",
                  "Solo estos datos pueden convertirse en afirmaciones personales.",
                ],
                [
                  "style_examples",
                  "Ejemplos históricos de estilo",
                  "Estos textos son referencias de voz, no una ficha profesional vigente.",
                ],
              ] as const
            ).map(([key, label, help]) => (
              <label key={key}>
                {label}
                <small>{help}</small>
                <textarea
                  rows={
                    key === "profile" ||
                    key === "projects" ||
                    key === "style_examples"
                      ? 5
                      : 3
                  }
                  value={draft[key]}
                  onChange={(e) =>
                    setDraft({ ...draft, [key]: e.target.value })
                  }
                  maxLength={
                    key === "style_examples"
                      ? 20000
                      : key === "profile" || key === "projects"
                        ? 12000
                        : key === "confirmed_facts"
                          ? 10000
                          : 5000
                  }
                />
              </label>
            ))}
            <label className="upload-control">
              <Upload size={18} />
              Importar referencia de texto
              <input
                type="file"
                accept=".txt,.md"
                onChange={(e) => {
                  if (e.target.files?.[0]) importText(e.target.files[0]);
                  e.target.value = "";
                }}
              />
            </label>
            <small>
              TXT o Markdown UTF-8, hasta 2 MB. Para otros documentos, copia el
              contenido a texto.
            </small>
            <details className="metadata-panel">
              <summary>
                Procedencia de referencias ({draft.references.length})
              </summary>
              <label>
                Referencias en JSON
                <textarea
                  rows={8}
                  defaultValue={JSON.stringify(draft.references, null, 2)}
                  onBlur={(e) => {
                    try {
                      const refs = JSON.parse(e.target.value);
                      if (Array.isArray(refs))
                        setDraft({ ...draft, references: refs });
                    } catch {
                      action(() =>
                        Promise.reject(
                          new Error("Revisa el JSON de las referencias."),
                        ),
                      );
                    }
                  }}
                />
              </label>
            </details>
            <small className="muted">
              Última actualización {dateTime(ctx.updated_at)} · revisión{" "}
              {ctx.revision}
            </small>
          </form>
        ) : (
          <Loading />
        )
      ) : tab === "conexiones" ? (
        <>
          <div className="connection-grid">
            {connections.map((c) => (
              <section className="connection-card" key={c.provider}>
                <div className="row">
                  <span className={"provider-icon " + c.provider}>
                    {c.provider === "openai"
                      ? "O"
                      : c.provider === "anthropic"
                        ? "A"
                        : c.provider === "wordpress"
                          ? "W"
                          : c.provider === "linkedin"
                            ? "in"
                            : c.provider === "ga4"
                              ? "G"
                              : "S"}
                  </span>
                  <Badge value={c.status} />
                </div>
                <h2>{providerNames[c.provider]}</h2>
                <p>{c.detail}</p>
                <small>
                  {c.has_secrets
                    ? "Credenciales guardadas · ••••••••"
                    : "Credenciales pendientes"}
                  {c.balance ? " · Saldo desconocido" : ""}
                </small>
                {c.checked_at && (
                  <small>Comprobación {dateTime(c.checked_at)}</small>
                )}
                <div className="connection-actions">
                  <button
                    className="secondary"
                    onClick={() => setEditConnection(c)}
                  >
                    Configurar
                  </button>
                  <button
                    className="text-button"
                    disabled={!c.has_secrets}
                    onClick={() =>
                      action(
                        () =>
                          api("/connections/" + c.provider + "/test", "POST"),
                        "Comprobación terminada. Consulta el estado de la conexión.",
                      )
                    }
                  >
                    <RefreshCw size={15} />
                    Comprobar
                  </button>
                </div>
                {c.provider === "linkedin" && c.has_secrets && (
                  <button
                    className="text-button"
                    onClick={() =>
                      action(async () => {
                        const result = await api<{ url: string }>(
                          "/oauth/linkedin/start",
                          "POST",
                        );
                        location.assign(result.url);
                      })
                    }
                  >
                    Autorizar LinkedIn
                    <ArrowUpRight size={16} />
                  </button>
                )}
                {["openai", "anthropic"].includes(c.provider) && (
                  <a
                    className="text-button"
                    href={
                      c.provider === "openai"
                        ? "https://platform.openai.com/settings/organization/billing/overview"
                        : "https://console.anthropic.com/settings/billing"
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    Panel de facturación
                    <ExternalLink size={14} />
                  </a>
                )}
              </section>
            ))}
          </div>
          <section className="settings-panel">
            <div className="section-heading">
              <div>
                <span className="eyebrow">DATOS REALES, BAJO DEMANDA</span>
                <h2>Estadísticas del contenido</h2>
                <p>{metrics?.message || "Aún no hay datos consultados."}</p>
              </div>
            </div>
            <form
              className="metrics-controls"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                action(
                  () =>
                    api("/sync/metrics", "POST", {
                      start: f.get("start"),
                      end: f.get("end"),
                    }),
                  "Consulta de métricas iniciada.",
                );
              }}
            >
              <label>
                Desde
                <input
                  name="start"
                  type="date"
                  required
                  defaultValue={new Date(Date.now() - 30 * 86400000)
                    .toISOString()
                    .slice(0, 10)}
                />
              </label>
              <label>
                Hasta
                <input
                  name="end"
                  type="date"
                  required
                  defaultValue={new Date(Date.now() - 3 * 86400000)
                    .toISOString()
                    .slice(0, 10)}
                />
              </label>
              <button className="primary">
                <RefreshCw size={17} />
                Actualizar datos
              </button>
            </form>
            {metrics?.signals.length ? (
              <div className="metrics-list">
                {metrics.signals.map((s, index) => (
                  <article key={index}>
                    <div className="row">
                      <strong>{s.title}</strong>
                      <Badge value={s.quality} />
                    </div>
                    <small>
                      {providerNames[s.provider]} · {s.start} → {s.end} ·{" "}
                      {s.topic} · {s.content_type}
                    </small>
                    <div className="metric-values">
                      {Object.entries(s.values).map(([k, v]) => (
                        <span key={k}>
                          {(
                            {
                              clicks: "Clics",
                              impressions: "Impresiones",
                              ctr: "CTR",
                              position: "Posición",
                              sessions: "Sesiones por página",
                              views: "Vistas",
                              engaged_sessions: "Sesiones con interacción",
                              events: "Eventos",
                              engagement_rate: "Ratio de interacción",
                            } as Record<string, string>
                          )[k] || k}
                          <strong>
                            {["ctr", "engagement_rate"].includes(k)
                              ? (v * 100).toFixed(2) + " %"
                              : v.toLocaleString("es-ES", {
                                  maximumFractionDigits: 2,
                                })}
                          </strong>
                        </span>
                      ))}
                    </div>
                    <p>{s.message}</p>
                    <small>
                      Antigüedad del artículo:{" "}
                      {s.article_age_days === null
                        ? "desconocida"
                        : `${s.article_age_days} días`}
                      .
                    </small>
                    {s.linkedin_sessions > 0 && (
                      <small>
                        {s.linkedin_sessions} sesiones por página con
                        origen/medio LinkedIn.
                      </small>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <div className="small-empty">
                No hay métricas de artículos disponibles. Esto indica ausencia
                de datos consultados, no rendimiento bajo.
              </div>
            )}
            {!!metrics?.comparisons?.length && (
              <div className="metrics-list">
                <h3>Periodos de igual duración</h3>
                {metrics.comparisons.map((comparison, index) => (
                  <article key={index}>
                    <div className="row">
                      <strong>{comparison.title}</strong>
                      <Badge value={comparison.quality} />
                    </div>
                    <small>
                      {providerNames[comparison.provider]} ·{" "}
                      {comparison.previous.join(" → ")} frente a{" "}
                      {comparison.current.join(" → ")}
                    </small>
                    <p>
                      {comparison.indicator === "clicks" ? "Clics" : "Vistas"}:
                      diferencia de{" "}
                      {comparison.difference.toLocaleString("es-ES")}; variación{" "}
                      {comparison.relative_change === null
                        ? "desconocida (base cero)"
                        : `${(comparison.relative_change * 100).toFixed(2)} %`}
                      .
                    </p>
                    <small>{comparison.message}</small>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : tab === "generacion" ? (
        <>
          <form
            className="settings-panel"
            onSubmit={(e) => {
              e.preventDefault();
              action(
                () => api("/preferences", "PUT", limits),
                "Preferencias guardadas. Las tareas activas mantienen sus límites originales.",
              );
            }}
          >
            <div className="section-heading">
              <div>
                <h2>Control de cada operación</h2>
                <p>
                  El modelo general se elige en la barra superior. No hay
                  publicación por calendario.
                </p>
              </div>
              <button className="primary">
                <Save size={17} />
                Guardar ajustes
              </button>
            </div>
            <div className="form-grid">
              <label>
                Nombre del estudio
                <input
                  value={limits.app_name}
                  onChange={(e) =>
                    setLimits({ ...limits, app_name: e.target.value })
                  }
                  maxLength={100}
                  required
                />
              </label>
              <label>
                Límite de gasto por operación (USD)
                <input
                  type="number"
                  min={0.01}
                  max={100}
                  step={0.01}
                  value={limits.max_cost}
                  onChange={(e) =>
                    setLimits({ ...limits, max_cost: e.target.value })
                  }
                  required
                />
              </label>
              {(
                [
                  ["max_ideas", "Máximo de ideas", 1, 20],
                  ["max_searches", "Búsquedas por investigación", 1, 5],
                  [
                    "max_output_tokens",
                    "Tokens de salida por llamada",
                    1000,
                    12000,
                  ],
                  [
                    "max_context_chars",
                    "Caracteres de contexto por llamada",
                    8000,
                    80000,
                  ],
                ] as const
              ).map(([k, label, min, max]) => (
                <label key={k}>
                  {label}
                  <input
                    type="number"
                    min={min}
                    max={max}
                    value={limits[k]}
                    onChange={(e) =>
                      setLimits({ ...limits, [k]: Number(e.target.value) })
                    }
                    required
                  />
                </label>
              ))}
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={limits.fallback}
                onChange={(e) =>
                  setLimits({ ...limits, fallback: e.target.checked })
                }
              />
              Permitir alternativa compatible dentro del límite de gasto
            </label>
            {limits.fallback && (
              <label>
                Alternativa
                <select
                  value={limits.fallback_provider + ":" + limits.fallback_model}
                  onChange={(e) => {
                    const m = catalog.models.find(
                      (m) => m.provider + ":" + m.id === e.target.value,
                    );
                    if (m)
                      setLimits({
                        ...limits,
                        fallback_provider: m.provider,
                        fallback_model: m.id,
                      });
                  }}
                >
                  {catalog.models.map((m) => (
                    <option
                      key={m.provider + m.id}
                      value={m.provider + ":" + m.id}
                    >
                      {m.provider} · {m.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <p className="muted">
              Se reserva gasto para fases restantes y respuestas inciertas. No
              se reintenta indefinidamente por errores de cuota, credenciales o
              permisos.
            </p>
          </form>
          <section className="settings-panel">
            <div className="section-heading">
              <div>
                <h2>Catálogo comprobado</h2>
                <p>
                  Versión {catalog.version} · tarifas en USD, sin conversión a
                  euros.
                </p>
              </div>
            </div>
            <div className="catalog-grid">
              {catalog.models.map((m) => (
                <article key={m.provider + m.id}>
                  <span className="eyebrow">{m.provider}</span>
                  <h3>{m.name}</h3>
                  <p>{m.description}</p>
                  <small>
                    Entrada {m.input ?? "desconocida"} / salida{" "}
                    {m.output ?? "desconocida"} USD por millón de tokens.
                    Búsqueda {m.search ?? "desconocida"} USD/uso.
                  </small>
                  <a href={m.source} target="_blank" rel="noreferrer">
                    Fuente · {m.verified}
                    <ArrowUpRight size={14} />
                  </a>
                  <CostEstimate estimate={m.estimate || null} />
                </article>
              ))}
            </div>
            <details className="metadata-panel">
              <summary>Editar catálogo y tarifas</summary>
              <p>
                Incluye solo modelos de texto cuya capacidad y disponibilidad
                hayas comprobado. Una tarifa null queda desconocida y bloquea
                operaciones con control de gasto.
              </p>
              <label>
                Catálogo en JSON
                <textarea
                  rows={12}
                  value={catText}
                  onChange={(e) => setCatText(e.target.value)}
                  spellCheck={false}
                />
              </label>
              <button
                className="secondary"
                onClick={() =>
                  action(
                    async () => api("/catalog", "PUT", JSON.parse(catText)),
                    "Catálogo actualizado.",
                  )
                }
              >
                Guardar catálogo versionado
              </button>
            </details>
          </section>
          <section className="settings-panel">
            <h2>Gasto registrado por la app</h2>
            <p className="cost-total">
              {dollars(costs?.calculated)}
              <small>
                calculado · {dollars(costs?.uncertain_reserved)} reservado por
                respuestas inciertas
              </small>
            </p>
            <p className="muted">{costs?.scope}</p>
            {costs?.calls.length ? (
              <div className="cost-call-list">
                {costs.calls.map((c) => (
                  <div key={c.id}>
                    <span>
                      <strong>{c.model}</strong>
                      <small>
                        {c.phase} · {dateTime(c.created_at)} · {c.status}
                      </small>
                    </span>
                    <span>
                      {c.uncertain
                        ? "Incierto · reserva " + dollars(c.estimated_cost)
                        : dollars(c.calculated_cost)}
                      <small>
                        {c.usage.input || 0} entrada · {c.usage.output || 0}{" "}
                        salida · {c.usage.searches || 0} búsquedas
                      </small>
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">Aún no hay llamadas IA registradas.</p>
            )}
          </section>
        </>
      ) : (
        <section className="settings-panel account-panel">
          <span className="eyebrow">ACCESO PRIVADO</span>
          <h2>Cambiar contraseña</h2>
          <p>Al guardar se cerrarán las otras sesiones de tu usuario.</p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.currentTarget,
                f = new FormData(form);
              const result = await action(
                () =>
                  api("/auth/password", "PUT", {
                    current: f.get("current"),
                    new: f.get("new"),
                  }),
                "Contraseña actualizada.",
              );
              if (result) form.reset();
            }}
          >
            <label>
              Contraseña actual
              <input
                name="current"
                type="password"
                autoComplete="current-password"
                required
              />
            </label>
            <label>
              Nueva contraseña
              <input
                name="new"
                type="password"
                autoComplete="new-password"
                minLength={12}
                maxLength={200}
                required
              />
            </label>
            <small>Mínimo 12 caracteres.</small>
            <button className="primary">
              <ShieldCheck size={17} />
              Actualizar contraseña
            </button>
          </form>
        </section>
      )}
      {editConnection && (
        <ConnectionDialog
          connection={editConnection}
          action={action}
          onClose={() => setEditConnection(null)}
        />
      )}
    </>
  );
}

function ConnectionDialog({
  connection: c,
  action,
  onClose,
}: {
  connection: Connection;
  action: Action;
  onClose: () => void;
}) {
  const definition = fields[c.provider],
    [busy, setBusy] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      config: Record<string, string> = {},
      secret: Record<string, string> = {};
    for (const [k] of definition.config) config[k] = String(f.get(k) || "");
    for (const [k] of definition.secrets)
      if (f.get(k)) secret[k] = String(f.get(k));
    setBusy(true);
    const result = await action(
      () =>
        api("/connections/" + c.provider, "PUT", { config, secrets: secret }),
      "Conexión guardada. Puedes comprobarla ahora.",
    );
    setBusy(false);
    if (result) onClose();
  }
  return (
    <Modal title={"Conectar " + providerNames[c.provider]} onClose={onClose}>
      <form onSubmit={save}>
        <p>{definition.note}</p>
        {definition.config.map(([k, label, type]) => (
          <label key={k}>
            {label}
            <input
              name={k}
              type={type}
              defaultValue={
                c.config[k] ||
                (k === "redirect_uri"
                  ? location.origin + "/api/oauth/linkedin/callback"
                  : "")
              }
              required
              maxLength={1000}
            />
          </label>
        ))}
        {definition.secrets.map(([k, label, type]) => (
          <label key={k}>
            {label}
            {type === "textarea" ? (
              <textarea
                name={k}
                rows={6}
                autoComplete="off"
                placeholder={
                  c.has_secrets
                    ? "•••••••• · deja vacío para conservar"
                    : "Pega aquí el JSON; se guardará cifrado"
                }
                maxLength={30000}
                required={!c.has_secrets}
              />
            ) : (
              <input
                name={k}
                type={type}
                autoComplete="new-password"
                placeholder={
                  c.has_secrets ? "•••••••• · deja vacío para conservar" : ""
                }
                maxLength={1000}
                required={!c.has_secrets}
              />
            )}
          </label>
        ))}
        <small className="muted">
          Las credenciales se cifran en el backend y no se devuelven completas
          al navegador.
        </small>
        <div className="modal-actions">
          {c.has_secrets && (
            <button
              type="button"
              className="danger"
              onClick={() => {
                if (
                  window.confirm("Eliminar esta conexión y sus credenciales?")
                )
                  action(async () => {
                    await api("/connections/" + c.provider, "DELETE");
                    onClose();
                  }, "Conexión eliminada.");
              }}
            >
              Desconectar
            </button>
          )}
          <button type="button" className="secondary" onClick={onClose}>
            Volver
          </button>
          <button className="primary" disabled={busy}>
            <Save size={16} />
            Guardar conexión
          </button>
        </div>
      </form>
    </Modal>
  );
}
