import { useState } from "react";
import { IconCopy } from "./Icons.jsx";

export default function TextPanel({
  title,
  value,
  latin = false,
  badge = null,
  actions = null,
  children = null,
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="card">
      <div className="textcard-head">
        <h3>
          {title}
          {badge}
        </h3>
        <div className="btnrow">
          {actions}
          <button
            type="button"
            className="toolbtn"
            onClick={copy}
            aria-label={`Copy ${title}`}
          >
            <IconCopy style={{ width: 13, height: 13 }} />
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <p className={latin ? "textcard-body latin" : "textcard-body"}>
        {value || "—"}
      </p>
      {children}
    </section>
  );
}