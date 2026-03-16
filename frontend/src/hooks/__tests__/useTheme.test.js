import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useTheme } from "../useTheme";

describe("useTheme", () => {
  let matchMediaListeners;

  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
    matchMediaListeners = [];

    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn((_, cb) => matchMediaListeners.push(cb)),
        removeEventListener: vi.fn(),
      })),
    });
  });

  it("defaults to dark when no localStorage and no system preference", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("reads theme from localStorage", () => {
    localStorage.setItem("focustest_theme", "light");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("falls back to system preference when no localStorage value", () => {
    window.matchMedia.mockImplementation((query) => ({
      matches: query === "(prefers-color-scheme: light)",
      media: query,
      addEventListener: vi.fn((_, cb) => matchMediaListeners.push(cb)),
      removeEventListener: vi.fn(),
    }));

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("toggleTheme switches from dark to light", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");

    act(() => result.current.toggleTheme());

    expect(result.current.theme).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(localStorage.getItem("focustest_theme")).toBe("light");
  });

  it("toggleTheme switches from light to dark", () => {
    localStorage.setItem("focustest_theme", "light");
    const { result } = renderHook(() => useTheme());

    act(() => result.current.toggleTheme());

    expect(result.current.theme).toBe("dark");
    expect(localStorage.getItem("focustest_theme")).toBe("dark");
  });

  it("responds to system preference changes when no explicit choice", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");

    // Simulate system preference change — should not override explicit localStorage
    act(() => result.current.toggleTheme()); // sets light explicitly
    expect(result.current.theme).toBe("light");

    // System change should not override explicit user choice
    act(() => {
      matchMediaListeners.forEach((cb) =>
        cb({ matches: false })
      );
    });
    expect(result.current.theme).toBe("light");
  });

  it("ignores invalid localStorage values", () => {
    localStorage.setItem("focustest_theme", "neon");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });
});
