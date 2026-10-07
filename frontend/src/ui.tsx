import { useEffect, useRef, type ReactNode } from "react";
import {
  X,
  ArrowUpRight,
  LoaderCircle,
  AlertCircle,
  Check,
  BookOpen,
} from "lucide-react";
import { safeUrl, dateTime, dollars } from "./api";
import type { Source, Estimate, Job } from "./types";

export function IconButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className="icon-button"
      aria-label={label}
      title={label}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = dialog.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className={wide ? "modal wide" : "modal"}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <IconButton label="Cerrar diálogo" onClick={onClose}>
          <X size={20} />
        </IconButton>
      </div>
      {children}
    </dialog>
  );
}
export function Badge({ value }: { value: string }) {
  const labels: Record<string, string> = {
    pendiente: "Pendiente",
    seleccionada: "Seleccionada",
    utilizada: "Utilizada",
    descartada: "Descartada",
    local: "Borrador local",
    draft: "Borrador WP",
    pending: "Revisión WP",
    publish: "Publicado",
    future: "Programado WP",
    private: "Privado",
    publicado: "Publicado",
    parcial: "Parcial",
    incierto: "Incierto",
    enviando: "Enviando",
    conectada: "Conectada",
    no_conectada: "No conectada",
    no_comprobada: "Sin comprobar",
    error: "Error",
    ejecutando: "En curso",
    terminado: "Terminado",
    fallido: "Fallido",
    cancelado: "Cancelado",
    interrumpido: "Interrumpido",
  };
  return <span className={"badge " + value}>{labels[value] || value}</span>;
}
export function Empty({
  title,
  text,
  children,
}: {
  title: string;
  text: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <BookOpen size={28} />
      </div>
      <h2>{title}</h2>
      <p>{text}</p>
      {children}
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={22} /> Cargando tu espacio…
    </div>
  );
}
export function ErrorBox({
  message,
  action,
}: {
  message: string;
  action?: string;
}) {
  return (
    <div className="error-box" role="alert">
      <AlertCircle size={19} />
      <div>
        {message}
        {action && <p>{action}</p>}
      </div>
    </div>
  );
}
export function Sources({ sources }: { sources: Source[] }) {
  return sources.length ? (
    <div className="sources">
      {sources.map((s) => (
        <a key={s.id} href={safeUrl(s.url)} target="_blank" rel="noreferrer">
          <span>
            {s.title || s.url}
            <small>
              {s.published_at
                ? "Publicado: " + s.published_at
                : "Fecha de publicación no verificada"}{" "}
              · Consultado {dateTime(s.consulted_at)}
            </small>
            {s.excerpt && <small>{s.excerpt}</small>}
          </span>
          <ArrowUpRight size={16} />
        </a>
      ))}
    </div>
  ) : (
    <p className="muted">No hay fuentes de investigación guardadas.</p>
  );
}
export function CostEstimate({ estimate }: { estimate: Estimate | null }) {
  return (
    estimate && (
      <div className="cost-estimate">
        <span>Estimación por publicación completa</span>
        <strong>
          {dollars(estimate.low)} — {dollars(estimate.high)}
        </strong>
        <small>
          USD · rango orientativo: investigación, artículo, LinkedIn, revisión y
          0–5 mejoras. 18.000–85.000 tokens de entrada y 7.000–40.000 de salida.
          El gasto real se registra aparte.
        </small>
      </div>
    )
  );
}
export function JobsPanel({
  jobs,
  onCancel,
  onResume,
}: {
  jobs: Job[];
  onCancel: (id: string) => void;
  onResume: (id: string) => void;
}) {
  return (
    <div className="jobs-list">
      {jobs.map((j) => (
        <article className="job" key={j.id}>
          <div className="row">
            <strong>{j.phase}</strong>
            <Badge value={j.state} />
          </div>
          <small>
            {j.kind} · {dateTime(j.created_at)} · {j.selection.provider}/
            {j.selection.model}
          </small>
          <progress
            max={100}
            value={j.progress}
            aria-label="Progreso del trabajo"
          />
          {j.error.message && (
            <ErrorBox message={j.error.message} action={j.error.action} />
          )}
          <div className="row">
            <small>{(j.result.explanation as string) || ""}</small>
            {["pendiente", "ejecutando"].includes(j.state) ? (
              <button
                className="text-button"
                onClick={() => onCancel(j.id)}
                disabled={j.cancel_requested}
              >
                {j.cancel_requested ? "Cancelación solicitada" : "Cancelar"}
              </button>
            ) : j.error.message && j.kind !== "li_publish" ? (
              <button className="text-button" onClick={() => onResume(j.id)}>
                Reintentar desde checkpoint
              </button>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}
export function Good({ children }: { children: ReactNode }) {
  return (
    <p className="good">
      <Check size={16} />
      {children}
    </p>
  );
}
