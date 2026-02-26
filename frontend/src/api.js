const BASE = "/api/sessions";

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

export async function listSessions({ limit = 10, offset = 0, search, sector, deleted } = {}) {
  const params = new URLSearchParams({ limit, offset });
  if (search) params.set("search", search);
  if (sector) params.set("sector", sector);
  if (deleted) params.set("deleted", "true");
  const resp = await fetch(`${BASE}?${params}`);
  if (!resp.ok) throw new Error("Failed to fetch sessions");
  return resp.json();
}

export async function deleteSession(id) {
  const resp = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Failed to delete session");
  return resp.json();
}

export async function restoreSession(id) {
  const resp = await fetch(`${BASE}/${id}/restore`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to restore session");
  return resp.json();
}

export async function permanentlyDeleteSession(id) {
  const resp = await fetch(`${BASE}/${id}/permanent`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Failed to permanently delete session");
  return resp.json();
}

export async function renameSession(id, name) {
  const resp = await fetch(`${BASE}/${id}/name`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Rename failed");
  }

  return resp.json();
}


export async function rerunSession(id, { question, sector, num_personas, demographic_filter }) {
  const body = { question };
  if (sector !== undefined) body.sector = sector;
  if (num_personas !== undefined) body.num_personas = num_personas;
  if (demographic_filter !== undefined) body.demographic_filter = demographic_filter;

  const resp = await fetch(`${BASE}/${id}/rerun`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Re-run failed");
  }

  return resp.json();
}

export async function runWtpAnalysis(id, { price_points, segment_by } = {}) {
  const body = {};
  if (price_points) body.price_points = price_points;
  if (segment_by) body.segment_by = segment_by;

  const resp = await fetch(`${BASE}/${id}/wtp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "WTP analysis failed");
  }

  return resp.json();
}

export function exportCsvUrl(id) {
  return `${BASE}/${id}/export/csv`;
}

export function exportPdfUrl(id) {
  return `${BASE}/${id}/export/pdf`;
}
