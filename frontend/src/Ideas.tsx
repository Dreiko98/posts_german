import { useState, useEffect, type FormEvent } from "react";
import {
  Plus,
  Sparkles,
  Search,
  ArrowUpRight,
  Check,
  RotateCcw,
  Archive,
  ExternalLink,
  Lightbulb,
  PenLine,
} from "lucide-react";
import { api, dateTime } from "./api";
import type { Idea, Job, Estimate } from "./types";
import type { Action } from "./App";
import { Modal, Badge, Empty, Loading, Sources, CostEstimate } from "./ui";

export function IdeasPage({
  action,
  refresh,
  openPub,
  jobs,
}: {
  action: Action;
  refresh: number;
  openPub: (id: string) => void;
  jobs: Job[];
}) {
  const [ideas, setIdeas] = useState<Idea[] | null>(null),
    [q, setQ] = useState(""),
    [filter, setFilter] = useState(""),
    [modal, setModal] = useState<"manual" | "batch" | null>(null),
    [detail, setDetail] = useState<Idea | null>(null),
    [prepare, setPrepare] = useState<Idea | null>(null),
    [discard, setDiscard] = useState<Idea | null>(null),
    [busy, setBusy] = useState(false),
    [estimate, setEstimate] = useState<Estimate | null>(null);
  useEffect(() => {
    api<Idea[]>("/ideas")
      .then(setIdeas)
      .catch((e) => action(() => Promise.reject(e)));
    api<Estimate>("/estimate")
      .then(setEstimate)
      .catch(() => {});
  }, [refresh]);
  const shown = (ideas || []).filter(
    (i) =>
      (!filter || i.status === filter) &&
      (!q ||
        (i.title + " " + i.summary + " " + i.topic)
          .toLowerCase()
          .includes(q.toLowerCase())),
  );
  const active = jobs.filter(
    (j) => j.kind === "ideas" && ["pendiente", "ejecutando"].includes(j.state),
  );
  async function generate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const f = new FormData(e.currentTarget);
    const result = await action(
      () =>
        api<Job>("/ideas/generate", "POST", {
          quantity: modal === "manual" ? 1 : Number(f.get("quantity")),
          instructions: f.get("instructions") || "",
          manual: modal === "manual",
          research: f.get("research") === "on",
        }),
      "Generación iniciada. Puedes seguir trabajando.",
    );
    setBusy(false);
    if (result) setModal(null);
  }
  async function state(i: Idea, status: string, reason = "") {
    const result = await action(
      () =>
        api("/ideas/" + i.id + "/state", "PUT", {
          status,
          discard_reason: reason,
          revision: i.revision,
        }),
      "Estado de la idea actualizado.",
    );
    if (result) {
      setDiscard(null);
      setDetail(null);
    }
  }
  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!prepare) return;
    setBusy(true);
    const f = new FormData(e.currentTarget);
    const result = await action(
      () =>
        api<{ publication_id: string }>(
          "/ideas/" + prepare.id + "/publication",
          "POST",
          {
            angle: f.get("angle"),
            notes: f.get("notes"),
            keyphrase: f.get("keyphrase"),
            research: f.get("research") === "on",
          },
        ),
      "Publicación en preparación.",
    );
    setBusy(false);
    if (result) {
      setPrepare(null);
      openPub(result.publication_id);
    }
  }
  function launch(i: Idea) {
    if (i.publication_id) openPub(i.publication_id);
    else setPrepare(i);
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">01 / EL PUNTO DE PARTIDA</span>
          <h1>
            Ideas<span className="accent">.</span>
          </h1>
          <p>Encuentra el enfoque que merece convertirse en contenido.</p>
        </div>
        <span className="heading-note">
          CON CONTEXTO.
          <br />
          CON INTENCIÓN.
        </span>
      </div>
      <section className="idea-entry-grid">
        <button className="entry-card" onClick={() => setModal("manual")}>
          <span className="entry-icon">
            <PenLine size={22} />
          </span>
          <div>
            <h2>Crear idea manualmente</h2>
            <p>
              Cuéntame qué tienes en mente.
              <br />
              La IA te ayuda a darle un enfoque.
            </p>
          </div>
          <Plus size={22} />
        </button>
        <button className="entry-card ai" onClick={() => setModal("batch")}>
          <span className="entry-icon">
            <Sparkles size={22} />
          </span>
          <div>
            <h2>Generar con IA</h2>
            <p>
              Explora temas a partir de tu contexto,
              <br />
              tu historial y las fuentes actuales.
            </p>
          </div>
          <ArrowUpRight size={22} />
        </button>
      </section>
      {active.map((j) => (
        <div className="inline-job" key={j.id}>
          <Sparkles size={17} />
          <span>{j.phase}</span>
          <progress max={100} value={j.progress} />
          <small>Puedes cerrar esta página.</small>
        </div>
      ))}
      <div className="section-heading">
        <h2>
          Tu banco de ideas <span>{ideas?.length ?? 0}</span>
        </h2>
        <p>Selecciona, revisa y conserva lo que aprendes.</p>
      </div>
      <div className="list-toolbar">
        <div className="filter-tabs">
          {[
            ["", "Todas"],
            ["pendiente", "Pendientes"],
            ["seleccionada", "Seleccionadas"],
            ["utilizada", "Utilizadas"],
            ["descartada", "Descartadas"],
          ].map(([v, l]) => (
            <button
              key={v}
              className={filter === v ? "selected" : ""}
              onClick={() => setFilter(v)}
            >
              {l}
            </button>
          ))}
        </div>
        <label className="search">
          <Search size={17} />
          <input
            aria-label="Buscar ideas"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar una idea…"
          />
        </label>
      </div>
      {ideas === null ? (
        <Loading />
      ) : shown.length ? (
        <div className="ideas-grid">
          {shown.map((i, index) => (
            <article className="idea-card" key={i.id}>
              <div className="row">
                <span className="card-index">
                  {String(index + 1).padStart(2, "0")} / {i.topic || "IDEA"}
                </span>
                <Badge value={i.status} />
              </div>
              <button className="card-title" onClick={() => setDetail(i)}>
                <h3>{i.title}</h3>
              </button>
              <p>{i.summary}</p>
              <div className="angle">
                <span>EL ENFOQUE</span>
                {i.angle}
              </div>
              <div className="card-meta">
                <span>{i.content_type}</span>
                <span>
                  {i.origin === "manual_guiado"
                    ? "Idea guiada"
                    : "Generada con IA"}
                </span>
                {i.current_news && <span>Actualidad</span>}
              </div>
              {i.relations.length > 0 && (
                <small className="relationship">
                  {i.relations.length} relación(es) con tu historial · revisa
                  las diferencias
                </small>
              )}
              <div className="card-actions">
                <button
                  className="text-button strong"
                  onClick={() => launch(i)}
                >
                  {i.publication_id ? "Abrir publicación" : "Crear publicación"}
                  <ArrowUpRight size={16} />
                </button>
                <div>
                  {i.status === "descartada" ? (
                    <button
                      className="icon-button"
                      aria-label="Recuperar idea"
                      onClick={() => state(i, "pendiente")}
                    >
                      <RotateCcw size={17} />
                    </button>
                  ) : (
                    i.status !== "utilizada" && (
                      <>
                        <button
                          className="icon-button"
                          aria-label={
                            i.status === "seleccionada"
                              ? "Desmarcar idea"
                              : "Seleccionar idea"
                          }
                          onClick={() =>
                            state(
                              i,
                              i.status === "seleccionada"
                                ? "pendiente"
                                : "seleccionada",
                            )
                          }
                        >
                          <Check size={18} />
                        </button>
                        <button
                          className="icon-button"
                          aria-label="Descartar idea"
                          onClick={() => setDiscard(i)}
                        >
                          <Archive size={17} />
                        </button>
                      </>
                    )
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title={
            q || filter
              ? "No hay ideas con este filtro"
              : "Todo empieza con una buena pregunta"
          }
          text={
            q || filter
              ? "Prueba otra búsqueda o cambia el estado."
              : "Escribe una intención o pide nuevas propuestas. Tu banco de ideas estará aquí."
          }
        >
          <button className="primary" onClick={() => setModal("manual")}>
            <Plus size={18} />
            Crear mi primera idea
          </button>
        </Empty>
      )}
      <div className="editorial-note">
        <Lightbulb size={18} />
        <p>
          Los temas relacionados pueden aportar algo nuevo. La diferencia está
          en la intención y el enfoque, no solo en el título.
        </p>
      </div>
      {modal && (
        <Modal
          title={
            modal === "manual"
              ? "Crear idea manualmente"
              : "Generar ideas con IA"
          }
          onClose={() => setModal(null)}
        >
          <form onSubmit={generate}>
            {modal === "manual" ? (
              <>
                <p>
                  Una intención basta para empezar. Desarrollaremos el enfoque y
                  lo compararemos con tu historial.
                </p>
                <label>
                  ¿Qué tienes en mente?
                  <textarea
                    name="instructions"
                    rows={5}
                    placeholder="Quiero escribir sobre…"
                    maxLength={5000}
                    required
                    autoFocus
                  />
                </label>
              </>
            ) : (
              <>
                <p>
                  Contexto, historial y estadísticas disponibles orientan las
                  propuestas. También dejamos espacio para explorar.
                </p>
                <label>
                  Cantidad de ideas
                  <input
                    type="number"
                    name="quantity"
                    min={1}
                    max={20}
                    defaultValue={5}
                    required
                  />
                </label>
                <label>
                  Temática o instrucciones{" "}
                  <span className="optional">opcional</span>
                  <textarea
                    name="instructions"
                    rows={3}
                    maxLength={5000}
                    placeholder="Por ejemplo: herramientas de IA con utilidad real"
                  />
                </label>
              </>
            )}
            <label className="checkbox">
              <input type="checkbox" name="research" defaultChecked />
              Investigar fuentes actuales con búsqueda web
            </label>
            <small className="muted">
              Para actualidad, mantén la búsqueda activada. El modelo y el
              límite de gasto se fijan al empezar.
            </small>
            <CostEstimate estimate={estimate} />
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setModal(null)}
              >
                Volver
              </button>
              <button className="primary" disabled={busy}>
                <Sparkles size={17} />
                {busy
                  ? "Iniciando…"
                  : modal === "manual"
                    ? "Desarrollar mi idea"
                    : "Generar propuestas"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {detail && (
        <IdeaDetail
          idea={detail}
          action={action}
          onClose={() => setDetail(null)}
          onLaunch={() => {
            launch(detail);
            setDetail(null);
          }}
        />
      )}
      {prepare && (
        <Modal title="Preparar publicación" onClose={() => setPrepare(null)}>
          <form onSubmit={create}>
            <h3>{prepare.title}</h3>
            <label>
              Enfoque
              <textarea
                name="angle"
                defaultValue={prepare.angle}
                rows={3}
                maxLength={5000}
              />
            </label>
            <label>
              Frase clave sugerida
              <input
                name="keyphrase"
                defaultValue={prepare.topic}
                maxLength={100}
              />
            </label>
            <label>
              Notas <span className="optional">opcional</span>
              <textarea
                name="notes"
                defaultValue={prepare.notes}
                rows={2}
                maxLength={5000}
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                name="research"
                defaultChecked={prepare.current_news}
              />
              Comprobar fuentes de nuevo
            </label>
            <Sources sources={prepare.sources} />
            <CostEstimate estimate={estimate} />
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setPrepare(null)}
              >
                Volver
              </button>
              <button className="primary" disabled={busy}>
                <Sparkles size={18} />
                {busy ? "Iniciando…" : "Preparar publicación"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {discard && (
        <Modal title="Descartar idea" onClose={() => setDiscard(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              state(
                discard,
                "descartada",
                String(new FormData(e.currentTarget).get("reason") || ""),
              );
            }}
          >
            <p>La idea se conserva y puedes recuperarla más adelante.</p>
            <label>
              Motivo <span className="optional">opcional</span>
              <textarea
                name="reason"
                rows={3}
                maxLength={2000}
                placeholder="Qué no encaja en este enfoque…"
              />
            </label>
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setDiscard(null)}
              >
                Volver
              </button>
              <button className="danger">Descartar idea</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function IdeaDetail({
  idea,
  action,
  onClose,
  onLaunch,
}: {
  idea: Idea;
  action: Action;
  onClose: () => void;
  onLaunch: () => void;
}) {
  const [editing, setEditing] = useState(false),
    [busy, setBusy] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const f = new FormData(e.currentTarget);
    const data = {
      revision: idea.revision,
      title: f.get("title"),
      summary: f.get("summary"),
      angle: f.get("angle"),
      topic: f.get("topic"),
      content_type: f.get("content_type"),
      rationale: f.get("rationale"),
      project_connection: f.get("project_connection"),
      notes: f.get("notes"),
      current_news: f.get("current_news") === "on",
    };
    const result = await action(
      () => api("/ideas/" + idea.id, "PUT", data),
      "Idea guardada.",
    );
    setBusy(false);
    if (result) onClose();
  }
  return (
    <Modal
      title={editing ? "Editar idea" : "Detalle de la idea"}
      onClose={onClose}
      wide
    >
      {editing ? (
        <form onSubmit={save}>
          {[
            ["title", "Título"],
            ["summary", "Resumen"],
            ["angle", "Enfoque"],
            ["topic", "Temática"],
            ["content_type", "Tipo de contenido"],
            ["rationale", "Por qué encaja"],
            ["project_connection", "Conexión con proyectos"],
            ["notes", "Notas personales"],
          ].map(([key, label]) => (
            <label key={key}>
              {label}
              {[
                "summary",
                "angle",
                "rationale",
                "project_connection",
                "notes",
              ].includes(key) ? (
                <textarea
                  name={key}
                  defaultValue={String(idea[key as keyof Idea] || "")}
                  maxLength={5000}
                  rows={3}
                />
              ) : (
                <input
                  name={key}
                  defaultValue={String(idea[key as keyof Idea] || "")}
                  maxLength={key === "title" ? 300 : 100}
                />
              )}
            </label>
          ))}
          <label className="checkbox">
            <input
              type="checkbox"
              name="current_news"
              defaultChecked={idea.current_news}
            />
            Tema de actualidad
          </label>
          <div className="modal-actions">
            <button
              type="button"
              className="secondary"
              onClick={() => setEditing(false)}
            >
              Volver
            </button>
            <button className="primary" disabled={busy}>
              Guardar cambios
            </button>
          </div>
        </form>
      ) : (
        <div className="idea-detail">
          <div className="row">
            <Badge value={idea.status} />
            <small>{dateTime(idea.created_at)}</small>
          </div>
          <h2>{idea.title}</h2>
          <p>{idea.summary}</p>
          <h4>Enfoque</h4>
          <p>{idea.angle}</p>
          <h4>Por qué encaja</h4>
          <p>{idea.rationale}</p>
          {idea.project_connection && (
            <>
              <h4>Conexión con proyectos</h4>
              <p>{idea.project_connection}</p>
            </>
          )}
          {idea.notes && (
            <>
              <h4>Tus notas</h4>
              <p>{idea.notes}</p>
            </>
          )}
          {idea.discard_reason && (
            <>
              <h4>Motivo de descarte conservado</h4>
              <p>{idea.discard_reason}</p>
            </>
          )}
          <h4>Relaciones con el historial</h4>
          {idea.relations.length ? (
            idea.relations.map((r, index) => (
              <div className="relation" key={index}>
                <Badge value={r.classification} />
                <p>{r.reason}</p>
                <small>Registro {r.id}</small>
              </div>
            ))
          ) : (
            <p className="muted">Sin relaciones señaladas.</p>
          )}
          <h4>Fuentes</h4>
          <Sources sources={idea.sources} />
          <h4>Señales estadísticas</h4>
          {idea.signals.length ? (
            idea.signals.map((s, index) => (
              <p key={index}>
                {String(s.message || "")} · {String(s.provider || "")}
              </p>
            ))
          ) : (
            <p className="muted">
              No había datos estadísticos disponibles en esta generación.
            </p>
          )}
          <div className="modal-actions">
            <button className="secondary" onClick={() => setEditing(true)}>
              <PenLine size={16} />
              Editar
            </button>
            <button className="primary" onClick={onLaunch}>
              {idea.publication_id ? "Abrir publicación" : "Crear publicación"}
              <ArrowUpRight size={17} />
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
