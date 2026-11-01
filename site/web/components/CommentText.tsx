import Link from "next/link";
import { Fragment } from "react";

// Only catalogue links and HTTPS references are interpreted. All other content
// remains React text, so comments cannot inject HTML or executable URLs.
export function CommentText({ text }: { text: string }) {
  const parts = text.split(/(\[[^\n]*?\]\((?:\/works\/XI-\d+|https:\/\/[^\s)]+)\))/g);
  return parts.map((part, index) => {
    const match = /^\[([^\n]*?)\]\((\/works\/XI-\d+|https:\/\/[^\s)]+)\)$/.exec(part);
    if (!match) return <Fragment key={index}>{part}</Fragment>;
    return match[2].startsWith("/works/")
      ? <Link className="text-link" key={index} href={match[2]}>{match[1]}</Link>
      : <a className="text-link" key={index} href={match[2]} target="_blank" rel="noopener noreferrer">{match[1]}<span className="sr-only">（新しいタブ）</span></a>;
  });
}
