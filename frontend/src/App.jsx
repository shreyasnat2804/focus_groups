import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import NewPitch from "./pages/NewPitch";
import PitchResults from "./pages/PitchResults";
import PitchList from "./pages/PitchList";
import About from "./pages/About";
import LandingPage from "./pages/LandingPage";
import Onboarding from "./pages/Onboarding";

const CHROMELESS_ROUTES = ["/", "/onboarding"];

function AppNav() {
  const location = useLocation();
  if (CHROMELESS_ROUTES.includes(location.pathname)) return null;

  return (
    <nav>
      <Link to="/dashboard" className="nav-brand">FocusTest</Link>
      <div className="nav-links">
        <Link to="/dashboard">Pitches</Link>
        <Link to="/about">About</Link>
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

export default function App() {
  return (
    <BrowserRouter>
      <AppBlobs />
      <AppNav />
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
