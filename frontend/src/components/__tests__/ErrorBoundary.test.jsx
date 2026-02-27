import { describe, it, expect, vi, beforeEach } from "vitest";
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
    expect(screen.getByText("test crash")).toBeInTheDocument();
  });

  it("renders custom fallback on error", () => {
    render(
      <ErrorBoundary
        fallback={({ error }) => <p>Custom: {error.message}</p>}
      >
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText("Custom: test crash")).toBeInTheDocument();
  });

  it("shows Try again button in default fallback", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });

  it("recovers after Try again when child stops throwing", async () => {
    const user = userEvent.setup();
    let shouldThrow = true;
    function MaybeThrow() {
      if (shouldThrow) throw new Error("boom");
      return <p>Recovered</p>;
    }

    render(
      <ErrorBoundary>
        <MaybeThrow />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Stop throwing before clicking reset
    shouldThrow = false;
    await user.click(screen.getByText("Try again"));
    expect(screen.getByText("Recovered")).toBeInTheDocument();
  });

  it("calls componentDidCatch and logs error", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(console.error).toHaveBeenCalled();
  });
});
