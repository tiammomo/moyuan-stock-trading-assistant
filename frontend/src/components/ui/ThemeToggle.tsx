"use client";

import { useEffect } from "react";
import { useThemeStore } from "@/stores/themeStore";

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useThemeStore();

  // Apply theme on mount
  useEffect(() => {
    const resolved = theme === "system" ? getSystemTheme() : theme;
    applyTheme(resolved);

    // Listen for system theme changes
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (theme === "system") {
        const newResolved = getSystemTheme();
        applyTheme(newResolved);
        useThemeStore.setState({ resolvedTheme: newResolved });
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [theme]);

  const cycleTheme = () => {
    const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
    setTheme(next);
  };

  const getIcon = () => {
    if (theme === "system") return "◐";
    return theme === "dark" ? "●" : "○";
  };

  const getLabel = () => {
    if (theme === "system") return "AUTO";
    return theme === "dark" ? "DARK" : "LIGHT";
  };

  return (
    <button
      onClick={cycleTheme}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono transition-all duration-200 hover:bg-muted"
      title={`Theme: ${theme}`}
    >
      <span className="text-base leading-none">{getIcon()}</span>
      <span className="text-muted-foreground">{getLabel()}</span>
    </button>
  );
}

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: "light" | "dark") {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}
