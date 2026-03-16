import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import NewPitch from "./pages/NewPitch";
import PitchResults from "./pages/PitchResults";
import PitchList from "./pages/PitchList";
import About from "./pages/About";
import LandingPage from "./pages/LandingPage";
import Onboarding from "./pages/Onboarding";
import { useTheme } from "./hooks/useTheme";

const CHROMELESS_ROUTES = ["/", "/onboarding"];

function ThemeToggle({ theme, toggleTheme }) {
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}

function AppNav({ theme, toggleTheme }) {
  const location = useLocation();
  if (CHROMELESS_ROUTES.includes(location.pathname)) return null;

  return (
    <nav>
      <Link to="/dashboard" className="nav-brand">FocusTest</Link>
      <div className="nav-links">
        <Link to="/dashboard">Pitches</Link>
        <Link to="/about">About</Link>
        <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        <Link to="/new" className="nav-new-pitch">+ New Pitch</Link>
      </div>
    </nav>
  );
}

function AppBlobs() {
  const location = useLocation();
  if (CHROMELESS_ROUTES.includes(location.pathname)) return null;

  return (
    <div className="app-blobs" aria-hidden="true">
      <div className="app-blob app-blob-1" />
      <div className="app-blob app-blob-2" />
      <div className="app-blob app-blob-3" />
    </div>
  );
}

export { ThemeToggle };

export default function App() {
  const { theme, toggleTheme } = useTheme();

  return (
    <BrowserRouter>
      <AppBlobs />
      <AppNav theme={theme} toggleTheme={toggleTheme} />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/dashboard" element={<main><PitchList /></main>} />
        <Route path="/new" element={<main><NewPitch /></main>} />
        <Route path="/sessions/:id" element={<main><PitchResults /></main>} />
        <Route path="/about" element={<main><About /></main>} />
      </Routes>
    </BrowserRouter>
  );
}
