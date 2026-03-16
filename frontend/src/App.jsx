import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import NewPitch from "./pages/NewPitch";
import PitchResults from "./pages/PitchResults";
import PitchList from "./pages/PitchList";
import About from "./pages/About";
import LandingPage from "./pages/LandingPage";
import Onboarding from "./pages/Onboarding";

function AppNav() {
  const location = useLocation();
  const hideNav = location.pathname === "/" || location.pathname === "/onboarding";
  if (hideNav) return null;

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

export default function App() {
  return (
    <BrowserRouter>
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
