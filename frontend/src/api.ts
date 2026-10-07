let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public action: string = "",
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const isForm = body instanceof FormData;
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    method === "GET" ? 15000 : 120000,
  );
  try {
    const response = await fetch("/api" + path, {
      method,
      credentials: "same-origin",
      headers: {
        ...(body && !isForm ? { "Content-Type": "application/json" } : {}),
        ...(method !== "GET" ? { "X-CSRF-Token": csrf } : {}),
      },
      body:
        body === undefined ? undefined : isForm ? body : JSON.stringify(body),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => null);
    if (controller.signal.aborted) throw new Error("request timed out");
    if (!response.ok)
      throw new ApiError(
        data?.error?.code || "error",
        data?.error?.message ||
          (response.status >= 500
            ? "El servicio no está disponible temporalmente."
            : "No se pudo completar la acción."),
        data?.error?.action || "",
      );
    if (data === null)
      throw new ApiError(
        "respuesta",
        "No se pudo leer la respuesta del servidor.",
      );
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      controller.signal.aborted ? "tiempo_agotado" : "red",
      controller.signal.aborted
        ? "El servidor no ha respondido a tiempo."
        : "No se pudo conectar con el servidor.",
      method === "GET"
        ? "Vuelve a intentarlo cuando el servicio esté disponible."
        : "Comprueba el estado de la operación antes de repetirla; puede haberse iniciado.",
    );
  } finally {
    clearTimeout(timeout);
  }
}
export const dateTime = (value: string) =>
  new Intl.DateTimeFormat("es-ES", {
    timeZone: "Europe/Madrid",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
export const dollars = (value: string | null | undefined) =>
  value == null
    ? "Desconocido"
    : new Intl.NumberFormat("es-ES", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 4,
      }).format(Number(value));
export const safeUrl = (value: string) =>
  /^https?:\/\//i.test(value) ? value : undefined;
