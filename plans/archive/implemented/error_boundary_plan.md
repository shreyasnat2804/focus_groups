# Fix: Add React Error Boundaries ✅ IMPLEMENTED

## Problem
The React frontend has no error boundaries. If any component throws during rendering (e.g., `undefined.map()` on a malformed API response, a Recharts prop type error, or a null reference in sentiment parsing), the entire app crashes to a blank white screen. The user gets no feedback, no way to recover, and has to manually reload the page.

This is especially risky because:
- `PitchResults` parses API response data with `.split()`, `.match()`, etc. — any unexpected format throws
- `VanWestendorpChart` and `DemandCurveChart` pass API data directly to Recharts — missing fields crash the chart
- `sentiment.js` does regex extraction on response text — edge cases can produce null refs

## Severity: MEDIUM

## Approach: Class-based ErrorBoundary + Per-section Wrapping

React error boundaries must be class components (hooks don't support `componentDidCatch`). We'll create one reusable `ErrorBoundary` component and wrap it at two levels:

1. **App-level** in `main.jsx` — catches catastrophic failures, shows a full-page fallback
2. **Section-level** around charts and response cards — isolates failures so the rest of the page still works

## Changes

### 1. Create `frontend/src/components/ErrorBoundary.jsx`

```jsx
import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          reset: this.handleReset,
        });
      }

      // Default fallback
      return (
        <div className="error-boundary">
          <h3>Something went wrong</h3>
          <p>{this.state.error?.message || "An unexpected error occurred."}</p>
          <button onClick={this.handleReset}>Try again</button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

**Props:**
- `children` — the component tree to protect
- `fallback` (optional) — render function `({ error, reset }) => JSX` for custom error UI

### 2. Add app-level boundary in `frontend/src/main.jsx`

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary
      fallback={({ reset }) => (
        <div className="error-page">
          <h1>FocusTest</h1>
          <p>Something went wrong. Please reload the page.</p>
          <button onClick={() => { reset(); window.location.href = "/"; }}>
            Go home
          </button>
        </div>
      )}
    >
      <App />
    </ErrorBoundary>
  </StrictMode>
);
```

### 3. Wrap chart components in `frontend/src/pages/PitchResults.jsx`

Identify the crash-prone sections in PitchResults and wrap each independently so a chart failure doesn't take down the whole results page:

```jsx
import ErrorBoundary from "../components/ErrorBoundary";

// In the JSX, wherever VanWestendorpChart is rendered:
<ErrorBoundary
  fallback={({ reset }) => (
    <div className="chart-error">
      <p>Failed to render price sensitivity chart.</p>
      <button onClick={reset}>Retry</button>
    </div>
  )}
>
  <VanWestendorpChart curves={wtpData.van_westendorp.curves} pricePoints={wtpData.van_westendorp} />
</ErrorBoundary>

// Wherever DemandCurveChart is rendered:
<ErrorBoundary
  fallback={({ reset }) => (
    <div className="chart-error">
      <p>Failed to render demand curve chart.</p>
      <button onClick={reset}>Retry</button>
    </div>
  )}
>
  <DemandCurveChart demandCurve={wtpData.gabor_granger.demand_curve} />
</ErrorBoundary>
```

### 4. Wrap response cards in `frontend/src/pages/PitchResults.jsx`

Individual response cards can fail due to bad sentiment parsing. Wrap the list so one bad card doesn't kill the page:

```jsx
{responses.map((r) => (
  <ErrorBoundary
    key={r.id}
    fallback={() => (
      <div className="card response-card error">
        <p>Failed to render this response.</p>
      </div>
    )}
  >
    <ResponseCard response={r} />
  </ErrorBoundary>
))}
```

### 5. Add CSS in `frontend/src/index.css`

```css
/* Error boundary styles */
.error-boundary {
  padding: 2rem;
  text-align: center;
  color: var(--text-secondary, #666);
}

.error-boundary h3 {
  color: var(--text-primary, #333);
  margin-bottom: 0.5rem;
}

.error-boundary button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid var(--border, #ddd);
  background: var(--bg-secondary, #f5f5f5);
  cursor: pointer;
}

.error-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.chart-error {
  padding: 2rem;
  text-align: center;
  background: var(--bg-secondary, #f9f9f9);
  border-radius: 8px;
  border: 1px dashed var(--border, #ddd);
}
```

## What This Does NOT Cover
- **Async errors** (failed fetch calls, rejected promises) — these are NOT caught by error boundaries. They should be handled with try/catch in the component's fetch logic + state like `{ error: "..." }`. The existing pages already do this with loading/error states.
- **Event handler errors** — also not caught by error boundaries. These should use standard try/catch.

Error boundaries only catch errors during **rendering**, **lifecycle methods**, and **constructors** of the tree below them.

## Tests

No test runner is configured for the frontend (see `frontend_tests_plan.md`). Manual verification:

1. **White-screen prevention**: Temporarily throw in `ResponseCard` render → verify the card shows "Failed to render" instead of a white screen
2. **Chart isolation**: Temporarily pass `null` as Recharts data → verify chart section shows error, but response cards still render
3. **App-level catch**: Temporarily throw in `App.jsx` render → verify the full-page fallback appears with "Go home" button
4. **Reset works**: After a section error, click "Try again" → verify the component re-renders

## Files Touched
- `frontend/src/components/ErrorBoundary.jsx` (new)
- `frontend/src/main.jsx` (wrap App)
- `frontend/src/pages/PitchResults.jsx` (wrap charts + response cards)
- `frontend/src/index.css` (error boundary styles)
