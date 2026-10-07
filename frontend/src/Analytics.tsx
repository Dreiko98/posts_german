import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Download,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { api } from "./api";
import type { Action } from "./App";
import type { Job } from "./types";
import { ErrorBox, Loading } from "./ui";

type Values = Record<string, number>;
type Point = { date: string; [metric: string]: number | string | null };
type Article = {
  id: string;
  title: string;
  url: string;
  topic: string;
  format: string;
  age_days: number | null;
  words: number;
  seo_score: number | null;
  ga4: Values;
  search_console: Values;
  observed_days: number;
  views_per_observed_day: number | null;
  change: number | null;
  ctr_interval: number[] | null;
  engagement_interval: number[] | null;
  sparse: boolean;
};
type Group = {
  label: string;
  articles: number;
  measured_articles: number;
  views: number;
  clicks: number;
  median_daily_views: number | null;
};
type Recommendation = {
  kind: string;
  title: string;
  publication_id: string | null;
  evidence: string;
  brief: string;
};
type Temporal = {
  metric: string;
  observed: number;
  anomalies: {
    date: string;
    value: number;
    baseline: number;
    direction: string;
  }[];
  weekday: { day: number; mean: number | null; n: number }[];
  forecast: null | {
    method: string;
    backtest_mae: number;
    message: string;
    points: { date: string; value: number; low: number; high: number }[];
  };
};
type Dashboard = {
  start: string;
  end: string;
  state: string;
  totals: { ga4: Values; search_console: Values };
  series: Point[];
  articles: Article[];
  themes: Group[];
  formats: Group[];
  queries: {
    query: string;
    publication_id: string | null;
    page: string;
    clicks: number;
    impressions: number;
    ctr: number;
    position: number;
    sparse: boolean;
  }[];
  recommendations: Recommendation[];
  sources: (Values & { source: string })[];
  temporal: Temporal[];
  correlations: { feature: string; n: number; rho: number | null }[];
  production?: {
    ideas: Record<string, number>;
    publications: number;
    wordpress_published: number;
    linkedin_published: number;
    ai_calls: number;
    calculated_cost: number;
    uncertain_reserved: number;
    message: string;
  };
  coverage: {
    ga4_days: number;
    search_console_days: number;
    days: number;
    unmapped_rows: number;
    partial_rows: number;
    imports: {
      provider: string;
      dataset: string;
      start: string;
      end: string;
      rows: number;
      imported_at: string;
    }[];
  };
  methodology: string[];
};
const number = (v: number | null | undefined, decimals = 0) =>
  v == null
    ? "—"
    : new Intl.NumberFormat("es-ES", {
        maximumFractionDigits: decimals,
      }).format(v);
const percent = (v: number | null | undefined) =>
  v == null ? "—" : number(v * 100, 1) + "%";
const shortDate = (v: string) =>
  new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" }).format(
    new Date(v + "T12:00:00"),
  );
const dateAgo = (days: number) =>
  new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
const labels: Record<string, string> = {
  views: "Vistas",
  sessions: "Sesiones",
  clicks: "Clics orgánicos",
  impressions: "Impresiones",
  words: "Longitud del artículo",
  age_days: "Antigüedad",
  seo_score: "Puntuación SEO",
};

function TimeChart({ points, metric }: { points: Point[]; metric: string }) {
  const [active, setActive] = useState<number | null>(null);
  useEffect(() => setActive(null), [points, metric]);
  const values = points.map((p) =>
    typeof p[metric] === "number" ? (p[metric] as number) : null,
  );
  const max = Math.max(1, ...values.filter((x): x is number => x !== null));
  const x = (i: number) => 52 + (i / Math.max(1, points.length - 1)) * 840;
  const y = (v: number) => 220 - (v / max) * 190;
  const paths = (data: (number | null)[]) => {
    const pieces: string[] = [];
    let current = "";
    data.forEach((v, i) => {
      if (v === null) {
        if (current) pieces.push(current);
        current = "";
      } else {
        current += `${current ? " L" : "M"}${x(i)},${y(v)}`;
      }
    });
    if (current) pieces.push(current);
    return pieces;
  };
  const rolling = values.map((_, i) =>
    i < 6 || values.slice(i - 6, i + 1).some((v) => v === null)
      ? null
      : (values.slice(i - 6, i + 1) as number[]).reduce((a, b) => a + b, 0) / 7,
  );
  return (
    <div className="analytics-chart">
      <div className="chart-readout" aria-live="polite">
        {active !== null && points[active]
          ? `${shortDate(points[active].date)} · ${number(values[active])} ${labels[metric].toLowerCase()}`
          : "Pasa el cursor o enfoca un punto para consultar el día"}
      </div>
      <svg
        viewBox="0 0 920 265"
        role="img"
        aria-label={`${labels[metric]} diarios y media móvil de siete días. Los huecos indican ausencia de observaciones.`}
      >
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line
              x1="52"
              x2="892"
              y1={y(v * max)}
              y2={y(v * max)}
              stroke="var(--border)"
            />
            <text x="44" y={y(v * max) + 4} textAnchor="end">
              {number(v * max)}
            </text>
          </g>
        ))}
        {paths(values).map((d, i) => (
          <path
            key={i}
            d={d}
            stroke="var(--accent)"
            strokeWidth="2"
            fill="none"
          />
        ))}
        {paths(rolling).map((d, i) => (
          <path
            key={i}
            d={d}
            stroke="var(--warning)"
            strokeWidth="2"
            strokeDasharray="5 4"
            fill="none"
          />
        ))}
        {values.map((v, i) =>
          v === null ? null : (
            <circle
              key={i}
              cx={x(i)}
              cy={y(v)}
              r={active === i ? 5 : 3}
              fill="var(--accent)"
              tabIndex={0}
              aria-label={`${points[i].date}: ${number(v)} ${labels[metric]}`}
              onFocus={() => setActive(i)}
              onMouseEnter={() => setActive(i)}
            >
              <title>
                {points[i].date}: {number(v)}
              </title>
            </circle>
          ),
        )}
        {[0, Math.floor((points.length - 1) / 2), points.length - 1]
          .filter((v, i, a) => a.indexOf(v) === i && points[v])
          .map((i) => (
            <text key={i} x={x(i)} y="250" textAnchor="middle">
              {shortDate(points[i].date)}
            </text>
          ))}
      </svg>
      <div className="chart-legend">
        <span>● Diario</span>
        <span>┄ Media móvil 7 días</span>
        <span>Huecos = sin observación</span>
      </div>
    </div>
  );
}

function Groups({ rows }: { rows: Group[] }) {
  return (
    <div className="analytics-table-wrap">
      <table className="analytics-table">
        <thead>
          <tr>
            <th>Grupo</th>
            <th>Artículos con datos / total</th>
            <th>Vistas</th>
            <th>Clics</th>
            <th>Mediana vistas / día observado</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((g) => (
            <tr key={g.label}>
              <td>{g.label}</td>
              <td>
                {g.measured_articles} / {g.articles}
              </td>
              <td>{number(g.views)}</td>
              <td>{number(g.clicks)}</td>
              <td>{number(g.median_daily_views, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AnalyticsPage({
  action,
  refresh,
  jobs,
  openPub,
  prepareIdea,
}: {
  action: Action;
  refresh: number;
  jobs: Job[];
  openPub: (id: string) => void;
  prepareIdea: (brief: string) => void;
}) {
  const [period, setPeriod] = useState({ start: dateAgo(92), end: dateAgo(3) });
  const [data, setData] = useState<Dashboard | null>(null),
    [error, setError] = useState("");
  const [tab, setTab] = useState("resumen"),
    [metric, setMetric] = useState("views");
  const [query, setQuery] = useState(""),
    [sort, setSort] = useState("views"),
    [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const importing = jobs.some(
    (j) =>
      j.kind === "metrics" && ["pendiente", "ejecutando"].includes(j.state),
  );
  useEffect(() => {
    let alive = true;
    setError("");
    api<Dashboard>(`/analytics?start=${period.start}&end=${period.end}`)
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [period, refresh]);
  const articles = useMemo(
    () =>
      (data?.articles || [])
        .filter(
          (a) =>
            (!topic || a.topic === topic) &&
            a.title.toLowerCase().includes(query.toLowerCase()),
        )
        .sort((a, b) => {
          const value = (a: Article) =>
            sort === "clicks"
              ? a.search_console.clicks || 0
              : sort === "daily"
                ? a.views_per_observed_day || 0
                : sort === "change"
                  ? (a.change ?? -Infinity)
                  : a.ga4.views || 0;
          return value(b) - value(a);
        }),
    [data, query, sort, topic],
  );
  async function sync() {
    setBusy(true);
    await action(
      () => api("/sync/metrics", "POST", { ...period, daily: true }),
      "Importación diaria iniciada. Consulta el progreso en Trabajos.",
    );
    setBusy(false);
  }
  function exportCSV() {
    if (!data) return;
    const cells = (x: unknown) =>
      '"' +
      String(x ?? "")
        .replace(/^[=+@-]/, "'$&")
        .replaceAll('"', '""') +
      '"';
    const csv = [
      ["fecha", "vistas", "sesiones", "clics", "impresiones"],
      ...data.series.map((p) => [
        p.date,
        p.views,
        p.sessions,
        p.clicks,
        p.impressions,
      ]),
    ]
      .map((r) => r.map(cells).join(";"))
      .join("\r\n");
    const url = URL.createObjectURL(
      new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `analitica-${period.start}-${period.end}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="analytics-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">DATOS QUE ORIENTAN DECISIONES</span>
          <h1>
            Analítica editorial<span className="accent">.</span>
          </h1>
          <p>Qué funciona, cómo evoluciona y dónde merece la pena escribir.</p>
        </div>
        <Activity size={30} />
      </div>
      <form
        className="analytics-controls"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setPeriod({
            start: String(f.get("start")),
            end: String(f.get("end")),
          });
        }}
        key={period.start + period.end}
      >
        <label>
          Desde
          <input
            type="date"
            name="start"
            defaultValue={period.start}
            required
          />
        </label>
        <label>
          Hasta
          <input
            type="date"
            name="end"
            defaultValue={period.end}
            max={dateAgo(0)}
            required
          />
        </label>
        <button className="secondary">Ver periodo</button>
        <button
          type="button"
          className="primary"
          disabled={busy || importing}
          onClick={sync}
        >
          <RefreshCw size={16} />
          {importing ? "Importando…" : "Importar datos diarios"}
        </button>
        <button
          type="button"
          className="text-button"
          onClick={exportCSV}
          disabled={!data}
        >
          <Download size={16} />
          CSV
        </button>
      </form>
      <p className="analytics-caption">
        La importación consulta GA4 y Search Console y guarda el detalle diario.
        No consume llamadas de IA. Máximo 180 días por consulta. Para importar
        otras fechas, pulsa primero «Ver periodo».
      </p>
      {error && <ErrorBox message={error} />}
      {!data ? (
        !error && <Loading />
      ) : (
        <>
          <div className="analytics-coverage">
            <span>
              GA4:{" "}
              <strong>
                {data.coverage.ga4_days}/{data.coverage.days} días observados
              </strong>
            </span>
            <span>
              Search Console:{" "}
              <strong>
                {data.coverage.search_console_days}/{data.coverage.days}
              </strong>
            </span>
            <span>
              {number(data.coverage.unmapped_rows)} filas sin artículo vinculado
            </span>
            <span>
              {data.coverage.partial_rows
                ? "Detalle con cobertura parcial"
                : "Consulta la procedencia al final"}
            </span>
          </div>
          {data.state === "sin_datos" && (
            <section className="analytics-empty">
              <h2>Construye tu histórico de datos</h2>
              <p>
                Primero sincroniza el blog en Publicaciones. Después pulsa
                «Importar datos diarios» para consultar las fuentes conectadas.
                Las métricas antiguas por periodos no se convierten en días
                inventados.
              </p>
            </section>
          )}
          <div
            className="analytics-tabs"
            role="tablist"
            aria-label="Análisis editorial"
          >
            {[
              ["resumen", "Evolución y decisiones"],
              ["contenido", "Qué funciona"],
              ["busquedas", "Demanda y canales"],
              ["modelos", "Análisis estadístico"],
            ].map(([id, label]) => (
              <button
                key={id}
                role="tab"
                aria-selected={tab === id}
                className={tab === id ? "active" : ""}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>
          {tab === "resumen" && (
            <>
              <div className="analytics-kpis">
                {[
                  ["Vistas del sitio", data.totals.ga4.views],
                  ["Sesiones del sitio", data.totals.ga4.sessions],
                  ["Clics desde Google", data.totals.search_console.clicks],
                  [
                    "Impresiones en Google",
                    data.totals.search_console.impressions,
                  ],
                ].map(([label, value]) => (
                  <article key={String(label)}>
                    <span>{label}</span>
                    <strong>{number(value as number | undefined)}</strong>
                    <small>Periodo seleccionado · fuente oficial</small>
                  </article>
                ))}
              </div>
              <section className="analytics-panel">
                <div className="row">
                  <h2>Evolución diaria</h2>
                  <select
                    aria-label="Métrica temporal"
                    value={metric}
                    onChange={(e) => setMetric(e.target.value)}
                  >
                    {["views", "sessions", "clicks", "impressions"].map((k) => (
                      <option key={k} value={k}>
                        {labels[k]}
                      </option>
                    ))}
                  </select>
                </div>
                <TimeChart points={data.series} metric={metric} />
              </section>
              <section className="analytics-panel">
                <h2>Próximas decisiones de contenido</h2>
                <p>
                  Oportunidades basadas en tus datos. Cada propuesta conserva su
                  evidencia; preparar una idea abre el formulario y la
                  generación necesita tu confirmación.
                </p>
                <div className="analytics-recommendations">
                  {data.recommendations.length ? (
                    data.recommendations.map((r, i) => (
                      <article key={i}>
                        <span className="eyebrow">{r.kind}</span>
                        <h3>{r.title}</h3>
                        <p>{r.evidence}</p>
                        <div className="row">
                          {r.publication_id && (
                            <button
                              className="text-button"
                              onClick={() => openPub(r.publication_id!)}
                            >
                              Abrir artículo <ArrowUpRight size={15} />
                            </button>
                          )}
                          <button
                            className="secondary"
                            onClick={() => prepareIdea(r.brief)}
                          >
                            <Sparkles size={15} />
                            Preparar idea
                          </button>
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="analytics-caption">
                      Todavía no hay evidencia suficiente para priorizar una
                      oportunidad. Amplía el periodo o importa el detalle
                      diario.
                    </p>
                  )}
                </div>
              </section>
            </>
          )}
          {tab === "contenido" && (
            <>
              <section className="analytics-panel">
                <h2>Rendimiento del histórico</h2>
                <div className="analytics-filters">
                  <input
                    aria-label="Buscar artículo"
                    placeholder="Buscar artículo…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <select
                    aria-label="Filtrar tema"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                  >
                    <option value="">Todos los temas</option>
                    {data.themes.map((t) => (
                      <option key={t.label}>{t.label}</option>
                    ))}
                  </select>
                  <select
                    aria-label="Ordenar artículos"
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                  >
                    <option value="views">Más vistas</option>
                    <option value="clicks">Más clics</option>
                    <option value="daily">Más vistas por día observado</option>
                    <option value="change">Mayor crecimiento observado</option>
                  </select>
                </div>
                <div className="analytics-table-wrap">
                  <table className="analytics-table">
                    <thead>
                      <tr>
                        <th>Artículo</th>
                        <th>Vistas / días observados</th>
                        <th>Clics / impresiones</th>
                        <th>CTR · intervalo 95%</th>
                        <th>Interacción</th>
                        <th>Cambio por día</th>
                        <th>Antigüedad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {articles.map((a) => (
                        <tr key={a.id}>
                          <td>
                            <button
                              className="text-button"
                              onClick={() => openPub(a.id)}
                            >
                              {a.title}
                            </button>
                            <small>
                              {a.topic} ·{" "}
                              {a.sparse ? "Muestra escasa" : "Observado"}
                            </small>
                          </td>
                          <td>
                            {number(a.ga4.views)} / {a.observed_days}
                            <small>
                              {number(a.views_per_observed_day, 1)} por día
                              observado
                            </small>
                          </td>
                          <td>
                            {number(a.search_console.clicks)} /{" "}
                            {number(a.search_console.impressions)}
                          </td>
                          <td>
                            {percent(a.search_console.ctr)}
                            <small>
                              {a.ctr_interval
                                ? `${percent(a.ctr_interval[0])}–${percent(a.ctr_interval[1])}`
                                : "Sin muestra"}
                            </small>
                          </td>
                          <td>{percent(a.ga4.engagement_rate)}</td>
                          <td>{percent(a.change)}</td>
                          <td>
                            {a.age_days == null ? "—" : `${a.age_days} días`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="analytics-caption">
                  Comparación entre mitades del periodo por día con observación;
                  exige al menos 7 días en cada mitad. El detalle por página
                  puede repetir sesiones entre páginas. La media por día
                  observado no equivale a la media por día natural.
                </p>
              </section>
              <section className="analytics-panel">
                <h2>Temas y categorías que atraen audiencia</h2>
                <Groups rows={data.themes} />
              </section>
              <section className="analytics-panel">
                <h2>Formatos de contenido</h2>
                <Groups rows={data.formats} />
                <p className="analytics-caption">
                  No se atribuye un formato a artículos históricos que todavía
                  no tienen esa clasificación.
                </p>
              </section>
            </>
          )}
          {tab === "busquedas" && (
            <>
              <section className="analytics-panel">
                <h2>Consultas reales de Google</h2>
                <p>
                  Qué busca la audiencia y qué páginas aparecen. Son filas
                  principales, con cobertura parcial.
                </p>
                <div className="analytics-table-wrap">
                  <table className="analytics-table">
                    <thead>
                      <tr>
                        <th>Consulta</th>
                        <th>Clics</th>
                        <th>Impresiones</th>
                        <th>CTR</th>
                        <th>Posición</th>
                        <th>Contenido</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.queries.map((q, i) => (
                        <tr key={i}>
                          <td>
                            {q.query}
                            <small>
                              {q.sparse
                                ? "Muestra escasa"
                                : "Al menos 100 impresiones"}
                            </small>
                          </td>
                          <td>{number(q.clicks)}</td>
                          <td>{number(q.impressions)}</td>
                          <td>{percent(q.ctr)}</td>
                          <td>{number(q.position, 1)}</td>
                          <td>
                            {q.publication_id ? (
                              <button
                                className="text-button"
                                onClick={() => openPub(q.publication_id!)}
                              >
                                Abrir artículo
                              </button>
                            ) : (
                              <span>{q.page}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="analytics-panel">
                <h2>Origen del tráfico por página</h2>
                <div className="analytics-table-wrap">
                  <table className="analytics-table">
                    <thead>
                      <tr>
                        <th>Origen / medio</th>
                        <th>Vistas</th>
                        <th>Sesiones por página</th>
                        <th>Interacción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.sources.map((s) => (
                        <tr key={s.source}>
                          <td>{s.source}</td>
                          <td>{number(s.views)}</td>
                          <td>{number(s.sessions)}</td>
                          <td>{percent(s.engagement_rate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="analytics-caption">
                  LinkedIn aparece cuando GA4 identifica ese origen. Esta
                  conexión no aporta las impresiones ni las reacciones del
                  perfil de LinkedIn.
                </p>
              </section>
            </>
          )}
          {tab === "modelos" && (
            <>
              <div className="analytics-model-grid">
                {data.temporal.map((t) => (
                  <section className="analytics-panel" key={t.metric}>
                    <span className="eyebrow">{labels[t.metric]}</span>
                    <h2>Tendencias y anomalías</h2>
                    <p>
                      {t.observed} días observados. Anomalías respecto a la
                      mediana móvil y desviación absoluta mediana; requieren 14
                      observaciones previas y un cambio absoluto de al menos 5.
                    </p>
                    {t.anomalies.length ? (
                      <ul>
                        {t.anomalies.map((a) => (
                          <li key={a.date}>
                            {shortDate(a.date)}:{" "}
                            <strong>{number(a.value)}</strong> · {a.direction}{" "}
                            respecto a una mediana de {number(a.baseline, 1)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="analytics-caption">
                        Sin anomalías detectadas con estos criterios.
                      </p>
                    )}
                    <h3>Proyección de la próxima semana</h3>
                    {t.forecast ? (
                      <>
                        <p>
                          {t.forecast.method} · error absoluto medio del
                          backtest: {number(t.forecast.backtest_mae, 1)}.
                        </p>
                        <div className="forecast-days">
                          {t.forecast.points.map((f) => (
                            <article key={f.date}>
                              <small>{shortDate(f.date)}</small>
                              <strong>{number(f.value, 1)}</strong>
                              <small>
                                {number(f.low, 1)}–{number(f.high, 1)}
                              </small>
                            </article>
                          ))}
                        </div>
                        <p className="analytics-caption">
                          {t.forecast.message}
                        </p>
                      </>
                    ) : (
                      <p className="analytics-caption">
                        Se necesitan al menos 42 días consecutivos con
                        observaciones. Con un histórico insuficiente no se
                        genera una predicción.
                      </p>
                    )}
                    <h3>Patrón por día de la semana</h3>
                    <div className="weekday-bars">
                      {t.weekday.map((w) => (
                        <div key={w.day}>
                          <span>
                            {
                              ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][
                                w.day
                              ]
                            }
                          </span>
                          <progress
                            max={Math.max(
                              1,
                              ...t.weekday.map((x) => x.mean || 0),
                            )}
                            value={w.mean || 0}
                          />
                          <strong>{number(w.mean, 1)}</strong>
                          <small>n={w.n}</small>
                        </div>
                      ))}
                    </div>
                    <p className="analytics-caption">
                      Describe cuándo se observa tráfico; no identifica el mejor
                      día para publicar.
                    </p>
                  </section>
                ))}
              </div>
              <section className="analytics-panel">
                <h2>Características del artículo y rendimiento</h2>
                <p>
                  Correlación de rangos Spearman con vistas por día observado.
                  Requiere 10 artículos con al menos 7 días observados.
                  Antigüedad, intención y cobertura pueden explicar la
                  asociación.
                </p>
                <div className="analytics-kpis">
                  {data.correlations.map((c) => (
                    <article key={c.feature}>
                      <span>{labels[c.feature]}</span>
                      <strong>
                        {c.rho === null ? "Sin muestra" : number(c.rho, 2)}
                      </strong>
                      <small>
                        {c.n} artículos elegibles · asociación, no causalidad
                      </small>
                    </article>
                  ))}
                </div>
              </section>
            </>
          )}
          {data.production && tab === "modelos" && (
            <section className="analytics-panel">
              <h2>Producción editorial y coste de IA</h2>
              <div className="analytics-kpis">
                <article>
                  <span>Biblioteca</span>
                  <strong>{data.production.publications}</strong>
                  <small>
                    {data.production.wordpress_published} publicados en
                    WordPress · {data.production.linkedin_published} en LinkedIn
                  </small>
                </article>
                <article>
                  <span>Coste calculado del periodo</span>
                  <strong>
                    {number(data.production.calculated_cost, 4)} USD
                  </strong>
                  <small>
                    {data.production.ai_calls} llamadas · reserva incierta:{" "}
                    {number(data.production.uncertain_reserved, 4)} USD
                  </small>
                </article>
                <article>
                  <span>Banco de ideas actual</span>
                  <strong>
                    {Object.values(data.production.ideas).reduce(
                      (a, b) => a + b,
                      0,
                    )}
                  </strong>
                  <small>
                    {Object.entries(data.production.ideas)
                      .map(([state, n]) => `${state}: ${n}`)
                      .join(" · ")}
                  </small>
                </article>
              </div>
              <p className="analytics-caption">{data.production.message}</p>
            </section>
          )}
          <details className="analytics-panel analytics-methods">
            <summary>Metodología, cobertura y procedencia</summary>
            <ul>
              {data.methodology.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
            <h3>Últimas importaciones del periodo</h3>
            {data.coverage.imports.length ? (
              data.coverage.imports.map((r, i) => (
                <p key={i}>
                  {r.provider} ·{" "}
                  {r.dataset === "site"
                    ? "Totales del sitio"
                    : "Detalle del contenido"}{" "}
                  · {r.start} → {r.end} · {number(r.rows)} filas ·{" "}
                  {new Date(r.imported_at).toLocaleString("es-ES", {
                    timeZone: "Europe/Madrid",
                  })}
                </p>
              ))
            ) : (
              <p>Todavía no hay importaciones diarias para este periodo.</p>
            )}
          </details>
        </>
      )}
    </div>
  );
}
