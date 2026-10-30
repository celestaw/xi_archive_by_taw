"use client";

import { useEffect, useRef, useState } from "react";
import { THEME_STORAGE_KEY } from "@/lib/theme";

type Theme = "light" | "dark";

function parseTheme(value: string | null): Theme | null {
  return value === "light" || value === "dark" ? value : null;
}

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const preference = useRef<Theme | null>(null);

  function applyTheme(theme: Theme) {
    document.documentElement.dataset.theme = theme;
    setDark(theme === "dark");
  }

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    try { preference.current = parseTheme(localStorage.getItem(THEME_STORAGE_KEY)); } catch {}

    function syncSystem() {
      applyTheme(preference.current ?? (media.matches ? "dark" : "light"));
    }
    function syncStorage(event: StorageEvent) {
      if (event.key !== THEME_STORAGE_KEY && event.key !== null) return;
      preference.current = parseTheme(event.newValue);
      syncSystem();
    }

    syncSystem();
    media.addEventListener("change", syncSystem);
    window.addEventListener("storage", syncStorage);
    return () => {
      media.removeEventListener("change", syncSystem);
      window.removeEventListener("storage", syncStorage);
    };
  }, []);

  function toggle() {
    const next: Theme = dark ? "light" : "dark";
    preference.current = next;
    applyTheme(next);
    try { localStorage.setItem(THEME_STORAGE_KEY, next); } catch {}
  }

  return (
    <button type="button" className="theme-toggle" onClick={toggle} role="switch" aria-checked={dark} aria-label="ダークモード">
      <span>ダーク</span>
      <span className="theme-switch-track" aria-hidden="true"><span className="theme-switch-thumb" /></span>
    </button>
  );
}
