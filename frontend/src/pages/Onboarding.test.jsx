import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Onboarding from "./Onboarding";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderOnboarding() {
  return render(
    <MemoryRouter>
      <Onboarding />
    </MemoryRouter>
  );
}

describe("Onboarding", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    localStorage.clear();
  });

  it("renders step 1 (welcome) by default", () => {
    renderOnboarding();
    expect(screen.getByText(/welcome to focustest/i)).toBeInTheDocument();
  });

  it("progresses to step 2 on next click", async () => {
    const user = userEvent.setup();
    renderOnboarding();
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/pick your sector/i)).toBeInTheDocument();
  });

  it("progresses to step 3 on second next click", async () => {
    const user = userEvent.setup();
    renderOnboarding();
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/you're all set/i)).toBeInTheDocument();
  });

  it("navigates to /new on finish", async () => {
    const user = userEvent.setup();
    renderOnboarding();
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create.*pitch/i }));
    expect(mockNavigate).toHaveBeenCalledWith("/new");
  });

  it("sets onboarding_complete in localStorage on finish", async () => {
    const user = userEvent.setup();
    renderOnboarding();
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create.*pitch/i }));
    expect(localStorage.getItem("focustest_onboarded")).toBe("true");
  });

  it("renders progress indicators", () => {
    renderOnboarding();
    const dots = document.querySelectorAll(".onboarding-dot");
    expect(dots.length).toBe(3);
  });

  it("allows going back from step 2", async () => {
    const user = userEvent.setup();
    renderOnboarding();
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /back/i }));
    expect(screen.getByText(/welcome to focustest/i)).toBeInTheDocument();
  });
});
