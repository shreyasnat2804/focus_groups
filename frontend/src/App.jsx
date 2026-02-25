import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import NewPitch from "./pages/NewPitch";
import PitchResults from "./pages/PitchResults";
import PitchList from "./pages/PitchList";

export default function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/" className="nav-brand">FocusTest</Link>
        <div className="nav-links">
          <Link to="/">Pitches</Link>
          <Link to="/new" className="nav-new-pitch">+ New Pitch</Link>
        </div>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<PitchList />} />
          <Route path="/new" element={<NewPitch />} />
          <Route path="/sessions/:id" element={<PitchResults />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
