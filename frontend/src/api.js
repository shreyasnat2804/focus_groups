const BASE = "/sessions";

export async function createSession({ question, sector, num_personas, demographic_filter }) {
  const body = { question, num_personas };
  if (sector) body.sector = sector;
  if (demographic_filter) body.demographic_filter = demographic_filter;

  const resp = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Request failed");
  }

  return resp.json();
}

export async function getSession(id) {
  const resp = await fetch(`${BASE}/${id}`);
  if (!resp.ok) throw new Error("Session not found");
  return resp.json();
}

export async function listSessions(limit = 20) {
  const resp = await fetch(`${BASE}?limit=${limit}`);
  if (!resp.ok) throw new Error("Failed to fetch sessions");
  return resp.json();
}

export function exportCsvUrl(id) {
  return `${BASE}/${id}/export/csv`;
}

export function exportPdfUrl(id) {
  return `${BASE}/${id}/export/pdf`;
}
