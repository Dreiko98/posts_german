import { useState, useEffect, type FormEvent } from "react";
import {
  Search,
  RefreshCw,
  ArrowUpRight,
  ArrowLeft,
  Save,
  Eye,
  History,
  Sparkles,
  Upload,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  FileDown,
  Link,
} from "lucide-react";
import { api, dateTime, safeUrl } from "./api";
import type { Publication, Article, Version, Job } from "./types";
import type { Action } from "./App";
import { Empty, Loading, Badge, Modal, Sources, ErrorBox } from "./ui";

const blank: Article = {
  title: "",
  seo_title: "",
  body: "",
  keyphrase: "",
  slug: "",
  meta_description: "",
  excerpt: "",
  categories: [],
  tags: [],
  image_alt: "",
};
export function PublicationsPage({
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
  const [pubs, setPubs] = useState<Publication[] | null>(null),
    [q, setQ] = useState(""),
    [status, setStatus] = useState("");
  useEffect(() => {
    api<Publication[]>("/publications")
      .then(setPubs)
      .catch((e) => action(() => Promise.reject(e)));
  }, [refresh]);
  const shown = (pubs || []).filter(
    (p) =>
      p.title.toLowerCase().includes(q.toLowerCase()) &&
      (!status || p.wp_status === status),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">02 / DEL ENFOQUE AL TEXTO</span>
          <h1>
            Publicaciones<span className="accent">.</span>
          </h1>
          <p>Dos canales, una idea. Revisa cada versión antes de enviarla.</p>
        </div>
        <button
          className="secondary"
          onClick={() =>
            action(
              () => api("/sync/blog", "POST"),
              "Importación del blog iniciada.",
            )
          }
        >
          <RefreshCw size={17} />
          Sincronizar blog
        </button>
      </div>
      <div className="publication-stats">
        <div>
          <span>EN TU ESTUDIO</span>
          <strong>
            {pubs?.length ?? "—"}
            <small>publicaciones</small>
          </strong>
        </div>
        <div>
          <span>WORDPRESS</span>
          <strong>
            {pubs?.filter((p) => p.wp_status === "publish").length ?? "—"}
            <small>publicadas</small>
          </strong>
        </div>
        <div>
          <span>LINKEDIN</span>
          <strong>
            {pubs?.filter((p) => p.li_status === "publicado").length ?? "—"}
            <small>publicadas</small>
          </strong>
        </div>
      </div>
      <div className="list-toolbar">
        <label className="search">
          <Search size={17} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar una publicación…"
            aria-label="Buscar publicaciones"
          />
        </label>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          aria-label="Filtrar estado WordPress"
        >
          <option value="">Todos los estados WordPress</option>
          <option value="local">Borrador local</option>
          <option value="draft">Borrador WordPress</option>
          <option value="publish">Publicado</option>
          <option value="parcial">Envío parcial</option>
        </select>
      </div>
      {pubs === null ? (
        <Loading />
      ) : shown.length ? (
        <div className="publication-list">
          <div className="publication-list-head">
            <span>PUBLICACIÓN</span>
            <span>WORDPRESS</span>
            <span>LINKEDIN</span>
            <span>SEO PROPIO</span>
            <span />
          </div>
          {shown.map((p) => (
            <button
              key={p.id}
              className="publication-row"
              onClick={() => openPub(p.id)}
            >
              <span className="publication-name">
                <span className="document-icon">
                  <Link size={20} />
                </span>
                <span>
                  <strong>{p.title}</strong>
                  <small>
                    {dateTime(p.updated_at)}
                    {p.external_change ? " · Cambios externos" : ""}
                    {jobs.some(
                      (j) =>
                        j.parameters.publication_id === p.id &&
                        ["pendiente", "ejecutando"].includes(j.state),
                    )
                      ? " · Trabajo en curso"
                      : ""}
                  </small>
                </span>
              </span>
              <span>
                <Badge value={p.wp_status} />
              </span>
              <span>
                <Badge value={p.li_status} />
                {p.li_stale && (
                  <small className="warning">Adaptación pendiente</small>
                )}
              </span>
              <span className="score-small">
                {p.evaluation && !p.evaluation_stale ? (
                  <>
                    <strong>{p.evaluation.score}</strong>
                    <small>/ 100</small>
                  </>
                ) : (
                  <small>Pendiente</small>
                )}
              </span>
              <ArrowUpRight size={20} />
            </button>
          ))}
        </div>
      ) : (
        <Empty
          title="Aquí tomarán forma tus ideas"
          text="Crea una publicación desde Ideas o importa tu historial de WordPress para empezar a trabajar."
        />
      )}
      <div className="editorial-note">
        <CheckCircle2 size={18} />
        <p>
          WordPress recibe borradores. La publicación final se hace desde
          WordPress; LinkedIn requiere tu acción expresa.
        </p>
      </div>
    </>
  );
}

export function Editor({
  id,
  action,
  refresh,
  jobs,
  onBack,
}: {
  id: string;
  action: Action;
  refresh: number;
  jobs: Job[];
  onBack: () => void;
}) {
  const [pub, setPub] = useState<Publication | null>(null),
    [wp, setWp] = useState<Article>(blank),
    [li, setLi] = useState(""),
    [channel, setChannel] = useState<"wordpress" | "linkedin">("wordpress"),
    [dirty, setDirty] = useState(false),
    [preview, setPreview] = useState(false),
    [versions, setVersions] = useState<Version[] | null>(null),
    [instructions, setInstructions] = useState(""),
    [busy, setBusy] = useState(false),
    [confirm, setConfirm] = useState(false),
    [taxonomy, setTaxonomy] = useState<{
      categories: { id: number; name: string }[];
      tags: { id: number; name: string }[];
    }>({ categories: [], tags: [] }),
    [alt, setAlt] = useState(""),
    [remoteId, setRemoteId] = useState("");
  const active = jobs.find(
    (j) =>
      j.parameters.publication_id === id &&
      ["pendiente", "ejecutando"].includes(j.state),
  );
  function load() {
    return api<Publication>("/publications/" + id).then((p) => {
      setPub(p);
      setWp((p.wordpress?.data as Article) || { ...blank, title: p.title });
      setLi((p.linkedin?.data as { text: string })?.text || "");
      setAlt(p.image?.alt || "");
      setDirty(false);
      return p;
    });
  }
  useEffect(() => {
    load().catch((e) => action(() => Promise.reject(e)));
    api<typeof taxonomy>("/taxonomy")
      .then(setTaxonomy)
      .catch(() => {});
  }, [id]);
  useEffect(() => {
    if (!dirty) load().catch(() => {});
  }, [refresh]);
  async function save() {
    if (!pub) return;
    setBusy(true);
    const result = await action(
      () =>
        api<Publication>("/publications/" + id + "/" + channel, "PUT", {
          revision: pub.revision,
          data: channel === "wordpress" ? wp : { text: li },
        }),
      "Versión guardada.",
    );
    if (result) {
      setPub(result);
      setDirty(false);
    }
    setBusy(false);
    return result;
  }
  async function run(name: string) {
    if (dirty) {
      const saved = await save();
      if (!saved) return;
    }
    setBusy(true);
    await action(
      () =>
        api<Job>("/publications/" + id + "/actions/" + name, "POST", {
          instructions,
        }),
      "Operación iniciada. Consulta el progreso en Trabajos.",
    );
    setBusy(false);
    setConfirm(false);
  }
  async function evaluate() {
    if (dirty) {
      const saved = await save();
      if (!saved) return;
    }
    await action(
      () => api("/publications/" + id + "/evaluate", "POST"),
      "Evaluación actualizada.",
    );
    await load();
  }
  function change<K extends keyof Article>(key: K, value: Article[K]) {
    setWp((x) => ({ ...x, [key]: value }));
    setDirty(true);
  }
  async function upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    const result = await action(
      () => api<Publication>("/publications/" + id + "/image", "POST", form),
      "Imagen guardada. Añade su texto alternativo.",
    );
    if (result) {
      setPub(result);
      setAlt(result.image?.alt || "");
    }
  }
  function exportArticle() {
    const blob = new Blob([wp.body], { type: "text/html;charset=utf-8" }),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = (wp.slug || "articulo") + ".html";
    a.click();
    URL.revokeObjectURL(url);
  }
  if (!pub) return <Loading />;
  const canPublish =
    pub.wp_status === "publish" &&
    pub.public_verified &&
    !pub.li_stale &&
    !!pub.linkedin &&
    !["publicado", "incierto", "enviando"].includes(pub.li_status) &&
    !active &&
    !dirty;
  const evaluation =
    pub.evaluation && !pub.evaluation_stale && !dirty ? pub.evaluation : null;
  return (
    <>
      <div className="editor-heading">
        <button
          className="text-button"
          onClick={() => {
            if (
              !dirty ||
              window.confirm("Hay cambios sin guardar. ¿Salir del editor?")
            )
              onBack();
          }}
        >
          <ArrowLeft size={16} />
          Publicaciones
        </button>
        <div className="row">
          <h1>{pub.title}</h1>
          <span className="badge">{dirty ? "Sin guardar" : "Guardado"}</span>
        </div>
        <div className="editor-controls">
          <div className="channel-tabs">
            <button
              className={channel === "wordpress" ? "active" : ""}
              onClick={() => {
                if (
                  !dirty ||
                  window.confirm(
                    "Descartar los cambios sin guardar de este canal?",
                  )
                ) {
                  setChannel("wordpress");
                  if (dirty) load();
                }
              }}
            >
              WordPress
              <Badge value={pub.wp_status} />
            </button>
            <button
              className={channel === "linkedin" ? "active" : ""}
              onClick={() => {
                if (
                  !dirty ||
                  window.confirm(
                    "Descartar los cambios sin guardar de este canal?",
                  )
                ) {
                  setChannel("linkedin");
                  if (dirty) load();
                }
              }}
            >
              LinkedIn
              <Badge value={pub.li_status} />
            </button>
          </div>
          <div className="row">
            <button
              className="secondary compact"
              onClick={() => setPreview(!preview)}
            >
              <Eye size={16} />
              {preview ? "Editar" : "Vista previa"}
            </button>
            <button
              className="secondary compact"
              onClick={() =>
                action(async () =>
                  setVersions(
                    await api<Version[]>("/publications/" + id + "/versions"),
                  ),
                )
              }
            >
              <History size={16} />
              <span>Versiones</span>
            </button>
            <button
              className="primary compact"
              disabled={busy || !!active || !dirty}
              onClick={save}
            >
              <Save size={16} />
              Guardar
            </button>
          </div>
        </div>
      </div>
      {active && (
        <div className="inline-job">
          <Sparkles size={18} />
          <span>{active.phase}</span>
          <progress max={100} value={active.progress} />
          <small>Las versiones completadas están guardadas.</small>
        </div>
      )}
      {pub.external_change && (
        <ErrorBox
          message="Se detectaron cambios externos en WordPress. Se conserva el texto local."
          action="Importa la versión remota para revisarla y preservar ambas versiones."
        />
      )}
      {pub.li_stale && channel === "linkedin" && (
        <div className="warning-box">
          <AlertTriangle size={18} />
          La adaptación procede de una versión anterior. Revísala y guarda, o
          actualízala con IA.
        </div>
      )}
      <div className="editor-layout">
        <section className="writing-pane">
          {channel === "wordpress" ? (
            <>
              <label className="title-field">
                TÍTULO DEL ARTÍCULO
                <input
                  value={wp.title}
                  onChange={(e) => change("title", e.target.value)}
                  maxLength={300}
                  disabled={!!active}
                />
              </label>
              <div className="body-toolbar">
                <span>
                  {preview
                    ? "VISTA PREVIA APROXIMADA"
                    : "CUERPO · HTML COMPATIBLE CON WORDPRESS"}
                </span>
                <button className="text-button" onClick={exportArticle}>
                  <FileDown size={15} />
                  Exportar
                </button>
              </div>
              {preview ? (
                <iframe
                  className="article-preview"
                  title="Vista previa aproximada de WordPress"
                  sandbox=""
                  srcDoc={
                    '<!doctype html><html lang="es"><meta charset="utf-8"><link rel="stylesheet" href="/preview.css"><body><h1>' +
                    escapeHtml(wp.title) +
                    "</h1>" +
                    wp.body +
                    "</body></html>"
                  }
                />
              ) : (
                <textarea
                  className="article-body"
                  aria-label="Cuerpo del artículo"
                  value={wp.body}
                  onChange={(e) => change("body", e.target.value)}
                  placeholder="El artículo aparecerá aquí al terminar la generación. También puedes escribir y guardar una versión propia."
                  disabled={!!active}
                />
              )}
              <p className="muted preview-note">
                El tema de WordPress determina el resultado final. La
                exportación conserva HTML seguro; al enviar se serializan los
                bloques nativos admitidos.
              </p>
              <details className="metadata-panel" open>
                <summary>Metadatos y búsqueda</summary>
                <div className="form-grid">
                  <label>
                    Título SEO
                    <input
                      value={wp.seo_title}
                      onChange={(e) => change("seo_title", e.target.value)}
                      maxLength={300}
                    />
                  </label>
                  <label>
                    Frase clave objetivo
                    <input
                      value={wp.keyphrase}
                      onChange={(e) => change("keyphrase", e.target.value)}
                      maxLength={100}
                    />
                  </label>
                  <label className="full">
                    Slug
                    <input
                      value={wp.slug}
                      onChange={(e) => change("slug", e.target.value)}
                      maxLength={200}
                    />
                  </label>
                  <label className="full">
                    Metadescripción
                    <textarea
                      value={wp.meta_description}
                      onChange={(e) =>
                        change("meta_description", e.target.value)
                      }
                      rows={3}
                      maxLength={500}
                    />
                    <small>{wp.meta_description.length} caracteres</small>
                  </label>
                  <label className="full">
                    Extracto
                    <textarea
                      value={wp.excerpt}
                      onChange={(e) => change("excerpt", e.target.value)}
                      rows={3}
                      maxLength={3000}
                    />
                  </label>
                  <label>
                    Categorías
                    <select
                      multiple
                      value={wp.categories.map(String)}
                      onChange={(e) =>
                        change(
                          "categories",
                          Array.from(e.target.selectedOptions).map((o) =>
                            Number(o.value),
                          ),
                        )
                      }
                    >
                      {taxonomy.categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Etiquetas
                    <select
                      multiple
                      value={wp.tags.map(String)}
                      onChange={(e) =>
                        change(
                          "tags",
                          Array.from(e.target.selectedOptions).map((o) =>
                            Number(o.value),
                          ),
                        )
                      }
                    >
                      {taxonomy.tags.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                {!taxonomy.categories.length && (
                  <small className="muted">
                    Sincroniza el blog para obtener categorías y etiquetas
                    reales.
                  </small>
                )}
              </details>
              <details className="metadata-panel" open>
                <summary>Imagen destacada manual</summary>
                {pub.image && (
                  <img
                    className="featured-preview"
                    src={pub.image.path}
                    alt={pub.image.alt}
                  />
                )}
                <label className="upload-control">
                  <Upload size={18} />
                  {pub.image ? "Cambiar imagen" : "Subir imagen"}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    disabled={!!active || busy}
                    onChange={(e) => {
                      if (e.target.files?.[0]) upload(e.target.files[0]);
                      e.target.value = "";
                    }}
                  />
                </label>
                <small className="muted">
                  JPEG, PNG o WebP · hasta 10 MB · se conserva la proporción.
                </small>
                {pub.image && (
                  <>
                    <label>
                      Texto alternativo
                      <input
                        value={alt}
                        onChange={(e) => setAlt(e.target.value)}
                        maxLength={1000}
                      />
                    </label>
                    <button
                      className="secondary compact"
                      onClick={() =>
                        action(
                          () => api("/files/" + pub.image!.id, "PUT", { alt }),
                          "Texto alternativo guardado. La evaluación necesita actualizarse.",
                        )
                      }
                      disabled={!!active}
                    >
                      Guardar alt
                    </button>
                    {pub.image.upload_uncertain && (
                      <label>
                        ID de Medios verificado en WordPress
                        <input
                          type="number"
                          min={1}
                          value={remoteId}
                          onChange={(e) => setRemoteId(e.target.value)}
                        />
                        <button
                          className="secondary"
                          disabled={!remoteId}
                          onClick={() =>
                            action(
                              () =>
                                api("/files/" + pub.image!.id, "PUT", {
                                  alt,
                                  wp_id: Number(remoteId),
                                }),
                              "Subida reconciliada.",
                            )
                          }
                        >
                          Registrar ID remoto
                        </button>
                      </label>
                    )}
                  </>
                )}
              </details>
            </>
          ) : (
            <>
              <label className="title-field">
                ADAPTACIÓN PARA TU PERFIL PERSONAL
              </label>
              {preview ? (
                <div className="linkedin-preview">
                  <div className="row">
                    <div className="avatar">G</div>
                    <div>
                      <strong>Germán Mallo</strong>
                      <small>Vista previa aproximada · Perfil personal</small>
                    </div>
                  </div>
                  <p>{li}</p>
                  {pub.canonical_url && (
                    <a
                      href={safeUrl(pub.canonical_url)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {pub.canonical_url}
                    </a>
                  )}
                </div>
              ) : (
                <textarea
                  className="linkedin-body"
                  aria-label="Texto LinkedIn"
                  value={li}
                  onChange={(e) => {
                    setLi(e.target.value);
                    setDirty(true);
                  }}
                  maxLength={3000}
                  disabled={!!active}
                  placeholder="Una idea, un aprendizaje o una reflexión que aporte valor por sí misma."
                />
              )}
              <div className="row">
                <small>{li.length} / 3.000 caracteres</small>
                <small>El enlace definitivo se añade antes del envío.</small>
              </div>
              <div className="warning-box">
                <AlertTriangle size={18} />
                El borrador de LinkedIn se guarda en esta app. Publicar lo envía
                a tu perfil.
              </div>
            </>
          )}
          <section className="ai-edit-box">
            <h3>
              <Sparkles size={18} />
              Revisar con una instrucción
            </h3>
            <label className="sr-only" htmlFor="instructions">
              Instrucciones de edición IA
            </label>
            <textarea
              id="instructions"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={3}
              maxLength={5000}
              placeholder="Por ejemplo: aclara el segundo apartado con una analogía, conservando las fuentes."
            />
            <button
              className="secondary"
              onClick={() =>
                run(channel === "wordpress" ? "correct" : "adapt-linkedin")
              }
              disabled={busy || !!active}
            >
              <Sparkles size={16} />
              {channel === "wordpress"
                ? "Aplicar cambios con IA"
                : "Actualizar adaptación con IA"}
            </button>
            <small>
              Se conserva la versión anterior. Se usa el modelo general al
              iniciar.
            </small>
          </section>
          <details className="metadata-panel">
            <summary>Fuentes de esta publicación</summary>
            <Sources sources={pub.sources} />
          </details>
        </section>
        <aside className="review-pane">
          <section className="review-card">
            <span className="eyebrow">ANÁLISIS REPRODUCIBLE</span>
            <div className="score-display">
              <strong>{evaluation ? evaluation.score : "—"}</strong>
              <span>/ 100</span>
            </div>
            <h3>
              {evaluation
                ? evaluation.score >= 70
                  ? "Umbral SEO alcanzado"
                  : "Requiere revisión SEO"
                : "Evaluación pendiente"}
            </h3>
            <p>
              Puntuación propia, inspirada en criterios de Yoast gratuito. No es
              un porcentaje oficial ni valida los hechos.
            </p>
            {evaluation && (
              <div className="evaluation-meta">
                <span>{evaluation.result.words} palabras</span>
                <span>Cobertura {evaluation.result.coverage} %</span>
                <span>Frase clave {evaluation.result.density} %</span>
              </div>
            )}
            <div className="review-actions">
              <button
                className="secondary"
                onClick={evaluate}
                disabled={busy || !!active}
              >
                Reevaluar
              </button>
              <button
                className="primary"
                onClick={() => run("correct")}
                disabled={busy || !!active || !pub.wordpress}
              >
                Corregir problemas
              </button>
            </div>
            <small>Reevaluar analiza. Corregir crea una nueva versión.</small>
          </section>
          {evaluation && (
            <>
              <section className="review-card">
                <h3>Problemas concretos</h3>
                {evaluation.result.checks.map((c) => (
                  <div
                    className={
                      "check-item " +
                      (!c.applicable ? "pending" : c.passed ? "pass" : "fail")
                    }
                    key={c.key}
                  >
                    {c.applicable && c.passed ? (
                      <CheckCircle2 size={16} />
                    ) : (
                      <AlertTriangle size={16} />
                    )}
                    <div>
                      <strong>{c.label}</strong>
                      {!c.applicable ? (
                        <small>Pendiente · no aplicable aún</small>
                      ) : (
                        c.advice && <small>{c.advice}</small>
                      )}
                    </div>
                  </div>
                ))}
              </section>
              <section className="review-card">
                <h3>Revisión editorial y evidencia</h3>
                {Object.values(evaluation.editorial).some((v) => v?.length) ? (
                  Object.entries(evaluation.editorial).map(([k, values]) =>
                    values?.map((v, index) => (
                      <p className="warning" key={k + index}>
                        {v}
                      </p>
                    )),
                  )
                ) : (
                  <p className="muted">
                    Sin revisión editorial guardada para esta versión. El
                    análisis técnico no comprueba afirmaciones.
                  </p>
                )}
                <h4>Legibilidad</h4>
                <p>
                  {evaluation.result.readability.long_sentence_percent} % de
                  frases de más de 25 palabras.
                </p>
                {evaluation.result.warnings.map((w, i) => (
                  <p key={i} className="warning">
                    {w}
                  </p>
                ))}
                <h4>Comprobaciones pendientes del sitio</h4>
                {evaluation.result.pending_site_checks.map((w, i) => (
                  <small className="block muted" key={i}>
                    {w}
                  </small>
                ))}
              </section>
            </>
          )}
          <section className="review-card platform-card">
            <span className="eyebrow">ENVÍO A PLATAFORMAS</span>
            <h3>Tu revisión decide</h3>
            <div className="row">
              <span>WordPress</span>
              <Badge value={pub.wp_status} />
            </div>
            {pub.wp_id && <small>ID remoto {pub.wp_id}</small>}
            {Object.entries(pub.confirmations).map(([key, value]) => (
              <small className="block" key={key}>
                {key === "content"
                  ? "Contenido"
                  : key === "seo"
                    ? "Campos SEO"
                    : "Imagen"}
                : {value ? "confirmado" : "pendiente"}
              </small>
            ))}
            <button
              className="primary"
              onClick={() => run("send-wordpress")}
              disabled={
                busy ||
                !!active ||
                !pub.wordpress ||
                ["publish", "future", "private"].includes(pub.wp_status)
              }
            >
              {pub.wp_id
                ? "Actualizar borrador en WordPress"
                : "Enviar borrador a WordPress"}
              <ArrowUpRight size={15} />
            </button>
            {pub.wp_id && (
              <>
                <a
                  className="button secondary"
                  href={
                    safeUrl(pub.canonical_url)
                      ? new URL(
                          "/wp-admin/post.php?post=" +
                            pub.wp_id +
                            "&action=edit",
                          pub.canonical_url,
                        ).href
                      : undefined
                  }
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir en WordPress
                  <ExternalLink size={15} />
                </a>
                <button
                  className="secondary"
                  onClick={() => run("check-wordpress")}
                  disabled={busy || !!active}
                >
                  Comprobar publicación
                </button>
              </>
            )}
            {pub.external_change && (
              <button
                className="secondary"
                onClick={() => run("import-remote")}
                disabled={busy || !!active}
              >
                Importar versión remota
              </button>
            )}
            <div className="platform-divider" />
            <div className="row">
              <span>LinkedIn</span>
              <Badge value={pub.li_status} />
            </div>
            <button
              className="secondary"
              onClick={() => run("adapt-linkedin")}
              disabled={busy || !!active || !pub.wordpress}
            >
              Actualizar adaptación de LinkedIn
            </button>
            <button
              className="primary"
              onClick={() => setConfirm(true)}
              disabled={!canPublish || busy}
            >
              Publicar en LinkedIn
              <ArrowUpRight size={15} />
            </button>
            {!canPublish && (
              <small>
                {pub.li_status === "incierto"
                  ? "Envío incierto. Comprueba tu perfil antes de reconciliar."
                  : pub.li_status === "publicado"
                    ? "Este post ya está publicado."
                    : "Requiere artículo WordPress público, comprobado y adaptación vigente guardada."}
              </small>
            )}
            {pub.li_status === "incierto" && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  action(
                    () =>
                      api(
                        "/publications/" + id + "/reconcile-linkedin",
                        "POST",
                        {
                          remote_id: f.get("remote_id"),
                          revision: pub.revision,
                        },
                      ),
                    "Resultado registrado tras comprobación manual.",
                  );
                }}
              >
                <label>
                  ID del post verificado
                  <input name="remote_id" required maxLength={200} />
                </label>
                <button className="secondary">Registrar resultado</button>
              </form>
            )}
          </section>
        </aside>
      </div>
      {versions && (
        <Modal
          title="Versiones guardadas"
          onClose={() => setVersions(null)}
          wide
        >
          {versions.length ? (
            versions.map((v) => (
              <div className="version-row" key={v.id}>
                <div>
                  <strong>
                    {v.channel === "wordpress"
                      ? (v.data as Article).title
                      : "Adaptación LinkedIn"}
                  </strong>
                  <small>
                    {v.reason.replaceAll("_", " ")} · {dateTime(v.created_at)}
                    {v.id === pub.best_wp ? " · Mejor versión del ciclo" : ""}
                  </small>
                  <details>
                    <summary>Consultar contenido</summary>
                    <pre>
                      {v.channel === "wordpress"
                        ? (v.data as Article).body
                        : (v.data as { text: string }).text}
                    </pre>
                  </details>
                </div>
                <button
                  className="secondary compact"
                  disabled={!!active}
                  onClick={() =>
                    action(async () => {
                      await api(
                        "/publications/" + id + "/restore/" + v.id,
                        "POST",
                        { expected_revision: pub.revision },
                      );
                      setVersions(null);
                      await load();
                    }, "Versión recuperada conservando el historial.")
                  }
                >
                  Recuperar
                </button>
              </div>
            ))
          ) : (
            <p className="muted">No hay versiones todavía.</p>
          )}
        </Modal>
      )}
      {confirm && (
        <Modal
          title="Publicar en tu perfil de LinkedIn"
          onClose={() => setConfirm(false)}
        >
          <p>
            Esta acción publica el texto en tu perfil personal. El servidor
            volverá a comprobar que el artículo WordPress es público y que la
            adaptación está vigente.
          </p>
          <p className="muted">Enlace: {pub.canonical_url}</p>
          <div className="modal-actions">
            <button className="secondary" onClick={() => setConfirm(false)}>
              Volver
            </button>
            <button
              className="primary"
              onClick={() => run("publish-linkedin")}
              disabled={busy}
            >
              Publicar en LinkedIn
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
function escapeHtml(value: string) {
  return value.replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
}
