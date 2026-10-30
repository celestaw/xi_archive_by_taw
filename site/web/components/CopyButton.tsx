"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { copyText } from "@/lib/clipboard";

type Props = {
  text: string;
  label?: string;
  children?: ReactNode;
  onManualCopy?: () => void;
  onStatus?: (message: string) => void;
};

export function CopyButton({ text, label = `「${text}」の曲名をコピー`, children, onManualCopy, onStatus }: Props) {
  const [state, setState] = useState<"idle" | "copying" | "copied" | "manual">("idle");
  const [copiedCount, setCopiedCount] = useState(0);
  const busy = useRef(false);
  const manualField = useRef<HTMLTextAreaElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const isTextButton = children !== undefined;

  useEffect(() => {
    if (state !== "copied") return;
    const timeout = window.setTimeout(() => { setState("idle"); onStatus?.(""); }, 2500);
    return () => window.clearTimeout(timeout);
  }, [state, copiedCount, onStatus]);

  useEffect(() => {
    if (state !== "manual" || onManualCopy) return;
    manualField.current?.focus({ preventScroll: true });
    manualField.current?.select();
  }, [state, onManualCopy]);

  async function copy() {
    if (busy.current) return;
    busy.current = true;
    setState("copying");
    onStatus?.("コピー中…");
    try {
      await copyText(text);
      setState("copied");
      setCopiedCount(count => count + 1);
      onStatus?.("コピーしました");
    } catch {
      setState("manual");
      onStatus?.("自動コピーできませんでした。選択された一覧を手動でコピーしてください。");
      onManualCopy?.();
    } finally {
      busy.current = false;
    }
  }

  function closeManualCopy() {
    setState("idle");
    trigger.current?.focus({ preventScroll: true });
  }

  return <span className={`copy-control${isTextButton ? " is-text" : ""}`} onClick={event => event.stopPropagation()} onKeyDown={event => {
    if (event.key === "Escape" && state === "manual" && !onManualCopy) {
      event.preventDefault();
      event.stopPropagation();
      closeManualCopy();
    }
  }} onBlur={event => {
    if (state === "manual" && !onManualCopy && !event.currentTarget.contains(event.relatedTarget)) setState("idle");
  }}>
    <button ref={trigger} type="button" className={`copy-button${isTextButton ? " copy-text-button" : ""}`} aria-label={label} title={label} aria-disabled={state === "copying"} aria-busy={state === "copying"} onClick={event => {
      event.preventDefault();
      event.stopPropagation();
      void copy();
    }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
        {state === "copied" ? <path d="m5 12 4 4L19 6" /> : <><rect x="8" y="8" width="12" height="13" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></>}
      </svg>
      {children}
    </button>
    {!onStatus && <span className={`copy-feedback${state === "manual" ? " is-manual" : ""}${state === "manual" && !onManualCopy ? " sr-only" : ""}`} role="status" aria-live="polite">
      {state === "copying" && "コピー中…"}
      {state === "copied" && "コピーしました"}
      {state === "manual" && (onManualCopy ? "自動コピーできませんでした。選択された一覧を手動でコピーしてください。" : "自動コピーできませんでした。下の曲名を選択してコピーしてください。")}
    </span>}
    {state === "manual" && !onManualCopy && <span className="copy-manual">
      <span>曲名を選択して手動でコピーしてください。</span>
      <textarea ref={manualField} aria-label="手動コピー用の曲名" readOnly rows={2} value={text} onFocus={event => event.currentTarget.select()} />
      <button type="button" className="text-link" onClick={closeManualCopy}>閉じる</button>
    </span>}
  </span>;
}
