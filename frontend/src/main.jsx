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
