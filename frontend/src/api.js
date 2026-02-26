const BASE = "/api/sessions";

const API_KEY = import.meta.env.VITE_API_KEY || "";

function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  return headers;
}

export async function createSession({ question, sector, num_personas, demographic_filter }) {
  const body = { question, num_personas };
  if (sector) body.sector = sector;
  if (demographic_filter) body.demographic_filter = demographic_filter;

  const resp = await fetch(BASE, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Request failed");
  }

  return resp.json();
}

export async function getSession(id) {
  const resp = await fetch(`${BASE}/${id}`, { headers: authHeaders() });
  if (!resp.ok) throw new Error("Session not found");
  return resp.json();
}

export async function listSessions({ limit = 10, offset = 0, search, sector, deleted } = {}) {
  const params = new URLSearchParams({ limit, offset });
  if (search) params.set("search", search);
  if (sector) params.set("sector", sector);
  if (deleted) params.set("deleted", "true");
  const resp = await fetch(`${BASE}?${params}`, { headers: authHeaders() });
  if (!resp.ok) throw new Error("Failed to fetch sessions");
  return resp.json();
}

export async function deleteSession(id) {
  const resp = await fetch(`${BASE}/${id}`, { method: "DELETE", headers: authHeaders() });
  if (!resp.ok) throw new Error("Failed to delete session");
  return resp.json();
}

export async function restoreSession(id) {
  const resp = await fetch(`${BASE}/${id}/restore`, { method: "POST", headers: authHeaders() });
  if (!resp.ok) throw new Error("Failed to restore session");
  return resp.json();
}

export async function permanentlyDeleteSession(id) {
  const resp = await fetch(`${BASE}/${id}/permanent`, { method: "DELETE", headers: authHeaders() });
  if (!resp.ok) throw new Error("Failed to permanently delete session");
  return resp.json();
}

export async function renameSession(id, name) {
  const resp = await fetch(`${BASE}/${id}/name`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
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
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Re-run failed");
  }

  return resp.json();
}

export async function runWtpAnalysis(id, {
  pricing_model,
  price_points,
  upfront_price_points,
  subscription_price_points,
  billing_interval,
  segment_by,
} = {}) {
  const body = {};
  if (pricing_model) body.pricing_model = pricing_model;
  if (price_points) body.price_points = price_points;
  if (upfront_price_points) body.upfront_price_points = upfront_price_points;
  if (subscription_price_points) body.subscription_price_points = subscription_price_points;
  if (billing_interval) body.billing_interval = billing_interval;
  if (segment_by) body.segment_by = segment_by;

  const resp = await fetch(`${BASE}/${id}/wtp`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
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
