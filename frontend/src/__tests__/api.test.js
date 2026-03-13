import { describe, it, expect, vi, beforeEach } from "vitest";

vi.stubEnv("VITE_API_KEY", "test-key-123");

describe("api module", () => {
  let api;

  beforeEach(async () => {
    vi.resetModules();
    global.fetch = vi.fn();
    api = await import("../api");
  });

  describe("authHeaders", () => {
    it("includes X-API-Key header in GET requests", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0 }),
      });

      await api.listSessions();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-API-Key": "test-key-123",
          }),
        })
      );
    });

    it("includes X-API-Key header in POST requests", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ session_id: "abc", status: "completed" }),
      });

      await api.createSession({ question: "Test?", num_personas: 5 });

      const [, options] = global.fetch.mock.calls[0];
      expect(options.headers["X-API-Key"]).toBe("test-key-123");
      expect(options.headers["Content-Type"]).toBe("application/json");
    });
  });

  describe("createSession", () => {
    it("sends POST with correct body", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ session_id: "abc" }),
      });

      await api.createSession({
        question: "Test?",
        num_personas: 5,
        sector: "tech",
      });

      const [url, options] = global.fetch.mock.calls[0];
      expect(url).toBe("/api/sessions");
      expect(options.method).toBe("POST");
      const body = JSON.parse(options.body);
      expect(body.question).toBe("Test?");
      expect(body.num_personas).toBe(5);
      expect(body.sector).toBe("tech");
    });

    it("omits sector when not provided", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ session_id: "abc" }),
      });

      await api.createSession({ question: "Test?", num_personas: 3 });

      const body = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(body.sector).toBeUndefined();
    });

    it("throws on non-200 response", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "Internal server error" }),
      });

      await expect(
        api.createSession({ question: "Test?", num_personas: 5 })
      ).rejects.toThrow("Internal server error");
    });

    it("throws fallback message when json parse fails", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.reject(new Error("parse error")),
      });

      await expect(
        api.createSession({ question: "Test?", num_personas: 5 })
      ).rejects.toThrow("Internal Server Error");
    });
  });

  describe("getSession", () => {
    it("fetches session by id", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: "abc-123", status: "completed" }),
      });

      const result = await api.getSession("abc-123");
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/sessions/abc-123",
        expect.objectContaining({ headers: expect.any(Object) })
      );
      expect(result.id).toBe("abc-123");
    });

    it("throws on not found", async () => {
      global.fetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(api.getSession("bad-id")).rejects.toThrow(
        "Session not found"
      );
    });
  });

  describe("listSessions", () => {
    it("passes query params for filtering", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0 }),
      });

      await api.listSessions({
        limit: 5,
        offset: 10,
        search: "test",
        sector: "tech",
        deleted: true,
      });

      const url = global.fetch.mock.calls[0][0];
      expect(url).toContain("limit=5");
      expect(url).toContain("offset=10");
      expect(url).toContain("search=test");
      expect(url).toContain("sector=tech");
      expect(url).toContain("deleted=true");
    });

    it("uses default limit and offset", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0 }),
      });

      await api.listSessions();

      const url = global.fetch.mock.calls[0][0];
      expect(url).toContain("limit=10");
      expect(url).toContain("offset=0");
    });
  });

  describe("deleteSession", () => {
    it("sends DELETE request", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "deleted" }),
      });

      await api.deleteSession("abc-123");

      const [url, options] = global.fetch.mock.calls[0];
      expect(url).toBe("/api/sessions/abc-123");
      expect(options.method).toBe("DELETE");
    });
  });

  describe("restoreSession", () => {
    it("sends POST to restore endpoint", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "restored" }),
      });

      await api.restoreSession("abc-123");

      const [url, options] = global.fetch.mock.calls[0];
      expect(url).toBe("/api/sessions/abc-123/restore");
      expect(options.method).toBe("POST");
    });
  });

  describe("exportCsvUrl / exportPdfUrl", () => {
    it("returns correct CSV URL", () => {
      expect(api.exportCsvUrl("abc-123")).toBe(
        "/api/sessions/abc-123/export/csv"
      );
    });

    it("returns correct PDF URL", () => {
      expect(api.exportPdfUrl("abc-123")).toBe(
        "/api/sessions/abc-123/export/pdf"
      );
    });
  });
});
