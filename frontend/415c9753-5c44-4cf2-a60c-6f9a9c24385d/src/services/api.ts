/**
 * src/services/api.ts
 * ====================
 * Client HTTP centralisé pour l'API FastAPI ALBARKA.
 *
 * - Lit l'URL de base depuis import.meta.env.VITE_API_URL (défaut : http://localhost:8000)
 * - Injecte automatiquement le JWT stocké en sessionStorage sur chaque requête
 * - Lève une ApiError avec le statut HTTP et le message retourné par FastAPI
 * - Fournit des helpers get / post / patch / del pour tous les services
 */

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '')
  ?? 'http://localhost:8000';

const SESSION_KEY = 'albarka.session';

// ── Erreur typée ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ── Récupération du token depuis la session ────────────────────────────────────

function getToken(): string | null {
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return (JSON.parse(raw) as { token?: string }).token ?? null;
  } catch {
    return null;
  }
}

// ── Requête de base ───────────────────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: { formData?: FormData } = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let bodyInit: BodyInit | undefined;

  if (options.formData) {
    // multipart/form-data : ne pas définir Content-Type, le navigateur le fait
    bodyInit = options.formData;
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    bodyInit = JSON.stringify(body);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: bodyInit,
  });

  if (!response.ok) {
    let message = `Erreur HTTP ${response.status}`;
    try {
      const err = await response.json();
      message = err.detail ?? message;
    } catch {
      /* pas de corps JSON */
    }
    throw new ApiError(response.status, message);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json() as Promise<T>;
}

// ── Helpers publics ───────────────────────────────────────────────────────────

export const api = {
  get: <T>(path: string) => request<T>('GET', path),

  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),

  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),

  del: <T = void>(path: string) => request<T>('DELETE', path),

  /** Upload multipart/form-data (fichiers CSV, Excel…) */
  upload: <T>(path: string, formData: FormData) =>
    request<T>('POST', path, undefined, { formData }),
};

// ── Construction des query strings ────────────────────────────────────────────

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== '',
  );
  if (entries.length === 0) return '';
  return '?' + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&');
}
