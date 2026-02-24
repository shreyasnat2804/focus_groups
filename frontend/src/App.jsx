import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import NewSession from "./pages/NewSession";
import SessionDetail from "./pages/SessionDetail";
import SessionList from "./pages/SessionList";

export default function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/">Sessions</Link>
        <Link to="/new">New Session</Link>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<SessionList />} />
          <Route path="/new" element={<NewSession />} />
          <Route path="/sessions/:id" element={<SessionDetail />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
