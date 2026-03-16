import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, Link } from "react-router-dom";

vi.mock("../../api", () => ({
  listSessions: vi.fn(),
  deleteSession: vi.fn(),
  restoreSession: vi.fn(),
  permanentlyDeleteSession: vi.fn(),
}));

import { listSessions } from "../../api";
import PitchList from "../PitchList";

function renderWithRouter() {
  return render(
    <MemoryRouter>
      <PitchList />
    </MemoryRouter>
  );
}

function renderWithNav() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <nav>
        <Link to="/">Pitches</Link>
        <Link to="/other">Other</Link>
      </nav>
      <Routes>
        <Route path="/" element={<PitchList />} />
        <Route path="/other" element={<div>Other Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("PitchList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading skeleton initially", () => {
    listSessions.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = renderWithRouter();
    expect(container.querySelector(".skeleton-card")).toBeInTheDocument();
  });

  it("renders session cards when data loads", async () => {
    listSessions.mockResolvedValueOnce({
      items: [
        {
          id: "abc-123",
          question: "Product: TestApp\n\nA cool app",
          sector: "tech",
          num_personas: 5,
          status: "completed",
          created_at: "2026-02-27T10:00:00Z",
          responses: [],
        },
      ],
      total: 1,
    });

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText("TestApp")).toBeInTheDocument();
    });
    expect(screen.getByText("5 people")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    // "tech" appears in both the sector filter dropdown and the card's sector tag
    const techElements = screen.getAllByText("tech");
    expect(techElements.length).toBeGreaterThanOrEqual(2);
  });

  it("shows empty state when no sessions", async () => {
    listSessions.mockResolvedValueOnce({
      items: [],
      total: 0,
    });

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText(/No pitches yet/)).toBeInTheDocument();
    });
  });

  it("shows error state on fetch failure", async () => {
    listSessions.mockRejectedValueOnce(new Error("Network error"));

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("renders pagination when more than one page", async () => {
    const items = Array.from({ length: 10 }, (_, i) => ({
      id: `id-${i}`,
      question: `Product: App${i}\n\nDesc`,
      sector: "tech",
      num_personas: 3,
      status: "completed",
      created_at: "2026-02-27T10:00:00Z",
      responses: [],
    }));

    listSessions.mockResolvedValueOnce({
      items,
      total: 25,
    });

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    });
    expect(screen.getByText("Previous")).toBeDisabled();
    expect(screen.getByText("Next")).toBeEnabled();
  });

  it("shows sentiment bar when responses have sentiment", async () => {
    listSessions.mockResolvedValueOnce({
      items: [
        {
          id: "abc-123",
          question: "Product: TestApp\n\nApp desc",
          sector: "tech",
          num_personas: 4,
          status: "completed",
          created_at: "2026-02-27T10:00:00Z",
          responses: [
            { response_text: "POSITIVE\nGreat!" },
            { response_text: "POSITIVE\nLove it!" },
            { response_text: "NEGATIVE\nBad" },
            { response_text: "MIXED\nOkay" },
          ],
        },
      ],
      total: 1,
    });

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText("50% positive")).toBeInTheDocument();
    });
  });

  it("resets deleted view when navigating via nav link while on same route", async () => {
    // Bug: clicking logo/Pitches nav link while viewing deleted sessions
    // doesn't reset showDeleted because the component stays mounted on "/"
    listSessions.mockResolvedValue({
      items: [],
      total: 0,
    });

    renderWithNav();
    await waitFor(() => {
      expect(screen.getByText(/No pitches yet/)).toBeInTheDocument();
    });

    // Toggle to deleted view
    const deletedToggle = screen.getByRole("button", { name: "Recently Deleted" });
    fireEvent.click(deletedToggle);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Recently Deleted" })).toBeInTheDocument();
    });

    // Click the "Pitches" nav link while already on "/" — component stays mounted
    fireEvent.click(screen.getByRole("link", { name: "Pitches" }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Your Pitches" })).toBeInTheDocument();
    });
  });

  it("displays singular 'person' for 1 persona", async () => {
    listSessions.mockResolvedValueOnce({
      items: [
        {
          id: "abc-123",
          question: "Product: Solo\n\nTest",
          sector: "tech",
          num_personas: 1,
          status: "completed",
          created_at: "2026-02-27T10:00:00Z",
          responses: [],
        },
      ],
      total: 1,
    });

    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText("1 person")).toBeInTheDocument();
    });
  });
});
