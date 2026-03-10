# Fix: Add Frontend Test Infrastructure and Tests — IMPLEMENTED 2026-02-27

## Problem
The frontend has zero tests and no test runner configured. `package.json` has no test script, no testing dependencies, and no test files exist. Any regression in API integration, routing, sentiment parsing, or component rendering goes undetected until manual testing.

The riskiest untested areas:
1. **`api.js`** — every fetch call, the `X-API-Key` header injection, error handling on non-200 responses
2. **`sentiment.js`** — regex-based parsing of POSITIVE/NEGATIVE/MIXED/NEUTRAL from response text, edge cases with missing labels
3. **`PitchResults.jsx`** — complex data flow from API → charts → cards, WTP analysis trigger, loading states
4. **`PitchList.jsx`** — pagination, search, sector filter, delete/restore, empty states

## Severity: MEDIUM

## Approach: Vitest + React Testing Library

Use **Vitest** (native Vite integration, same config, fast) with **@testing-library/react** (standard React testing approach, tests behavior not implementation).

## Changes

### 1. Install dependencies

```bash
cd frontend
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

### 2. Add test config to `frontend/vite.config.js`

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.js",
    css: false,
  },
});
```

### 3. Create `frontend/src/test-setup.js`

```js
import "@testing-library/jest-dom";
```

### 4. Add test script to `frontend/package.json`

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:run": "vitest run"
  }
}
```

### 5. Test files

#### `frontend/src/utils/__tests__/sentiment.test.js`

Tests the sentiment parsing utility, which extracts labels from Claude's response text.

```js
import { describe, it, expect } from "vitest";
import { extractSentiment, getSentimentColor } from "../sentiment";

describe("extractSentiment", () => {
  it("extracts POSITIVE from start of text", () => {
    expect(extractSentiment("POSITIVE\nI love this product!")).toBe("POSITIVE");
  });

  it("extracts NEGATIVE from start of text", () => {
    expect(extractSentiment("NEGATIVE\nThis is overpriced.")).toBe("NEGATIVE");
  });

  it("extracts MIXED from start of text", () => {
    expect(extractSentiment("MIXED\nSome good, some bad.")).toBe("MIXED");
  });

  it("extracts NEUTRAL from start of text", () => {
    expect(extractSentiment("NEUTRAL\nI have no strong opinion.")).toBe("NEUTRAL");
  });

  it("returns NEUTRAL for missing label", () => {
    expect(extractSentiment("Just a regular response")).toBe("NEUTRAL");
  });

  it("returns NEUTRAL for empty string", () => {
    expect(extractSentiment("")).toBe("NEUTRAL");
  });

  it("returns NEUTRAL for null/undefined", () => {
    expect(extractSentiment(null)).toBe("NEUTRAL");
    expect(extractSentiment(undefined)).toBe("NEUTRAL");
  });
});

describe("getSentimentColor", () => {
  it("returns correct colors for each sentiment", () => {
    expect(getSentimentColor("POSITIVE")).toBeDefined();
    expect(getSentimentColor("NEGATIVE")).toBeDefined();
    expect(getSentimentColor("MIXED")).toBeDefined();
    expect(getSentimentColor("NEUTRAL")).toBeDefined();
  });
});
```

#### `frontend/src/__tests__/api.test.js`

Tests the API client module — header injection, response handling, error paths.

```js
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock import.meta.env before importing the module
vi.stubEnv("VITE_API_KEY", "test-key-123");
vi.stubEnv("VITE_API_URL", "http://localhost:8000");

describe("api module", () => {
  let api;

  beforeEach(async () => {
    vi.resetModules();
    global.fetch = vi.fn();
    api = await import("../api");
  });

  it("includes X-API-Key header in requests", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0 }),
    });

    await api.fetchSessions();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-API-Key": "test-key-123",
        }),
      })
    );
  });

  it("throws on non-200 responses", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "Internal server error" }),
    });

    // Should reject or throw — test based on actual api.js implementation
    await expect(api.fetchSession("bad-id")).rejects.toThrow();
  });

  it("sends correct POST body for session creation", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ session_id: "abc", status: "completed", num_responses: 5 }),
    });

    await api.createSession({
      question: "Test?",
      num_personas: 5,
      sector: "tech",
    });

    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain("/api/sessions");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      question: "Test?",
      num_personas: 5,
      sector: "tech",
    });
  });
});
```

**Note**: The exact function names (`fetchSessions`, `fetchSession`, `createSession`) must match what's actually exported from `api.js`. Read `api.js` before implementing and adjust accordingly.

#### `frontend/src/components/__tests__/ErrorBoundary.test.jsx`

If `ErrorBoundary` is implemented per `error_boundary_plan.md`:

```jsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ErrorBoundary from "../ErrorBoundary";

function ThrowingComponent() {
  throw new Error("test crash");
}

function SafeComponent() {
  return <p>All good</p>;
}

describe("ErrorBoundary", () => {
  // Suppress console.error for intentional throws
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText("All good")).toBeInTheDocument();
  });

  it("renders default fallback on error", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders custom fallback on error", () => {
    render(
      <ErrorBoundary fallback={({ error }) => <p>Custom: {error.message}</p>}>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText("Custom: test crash")).toBeInTheDocument();
  });

  it("resets when try again is clicked", async () => {
    const user = userEvent.setup();
    // After reset, the component will throw again immediately,
    // so we test that the reset callback is invoked
    let renderCount = 0;
    function MaybeThrow() {
      renderCount++;
      if (renderCount <= 2) throw new Error("boom");
      return <p>Recovered</p>;
    }

    render(
      <ErrorBoundary>
        <MaybeThrow />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    await user.click(screen.getByText("Try again"));
    // Will throw again on re-render, showing fallback again
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });
});
```

#### `frontend/src/pages/__tests__/PitchList.test.jsx`

```jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock api module
vi.mock("../../api", () => ({
  fetchSessions: vi.fn(),
  deleteSession: vi.fn(),
  restoreSession: vi.fn(),
}));

import { fetchSessions } from "../../api";
import PitchList from "../PitchList";

function renderWithRouter() {
  return render(
    <MemoryRouter>
      <PitchList />
    </MemoryRouter>
  );
}

describe("PitchList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    fetchSessions.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithRouter();
    // Check for loading indicator (spinner, text, etc.)
    // Adjust selector based on actual PitchList implementation
  });

  it("renders session cards when data loads", async () => {
    fetchSessions.mockResolvedValueOnce({
      items: [
        {
          id: "abc-123",
          question: "What do you think of our app?",
          sector: "tech",
          num_personas: 5,
          status: "completed",
          created_at: "2026-02-27T10:00:00Z",
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
      has_more: false,
    });

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText(/What do you think of our app/)).toBeInTheDocument();
    });
  });

  it("shows empty state when no sessions", async () => {
    fetchSessions.mockResolvedValueOnce({
      items: [],
      total: 0,
      limit: 10,
      offset: 0,
      has_more: false,
    });

    renderWithRouter();
    await waitFor(() => {
      // Adjust text based on actual empty state message
      expect(screen.getByText(/no pitches/i)).toBeInTheDocument();
    });
  });

  it("shows error state on fetch failure", async () => {
    fetchSessions.mockRejectedValueOnce(new Error("Network error"));

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText(/error|failed/i)).toBeInTheDocument();
    });
  });
});
```

**Important**: All test assertions above reference text/elements that must match the actual component implementations. Read each component before writing the final tests and adjust selectors accordingly.

## Test Run Commands

```bash
# Run all frontend tests
cd frontend && npm test

# Run once (CI mode)
cd frontend && npm run test:run

# Run with coverage
cd frontend && npx vitest run --coverage
```

## Files Touched
- `frontend/package.json` (add dev dependencies + test scripts)
- `frontend/vite.config.js` (add test config)
- `frontend/src/test-setup.js` (new)
- `frontend/src/utils/__tests__/sentiment.test.js` (new)
- `frontend/src/__tests__/api.test.js` (new)
- `frontend/src/components/__tests__/ErrorBoundary.test.jsx` (new, depends on error_boundary_plan)
- `frontend/src/pages/__tests__/PitchList.test.jsx` (new)

## Dependencies on Other Plans
- `error_boundary_plan.md` — ErrorBoundary tests assume that component exists
