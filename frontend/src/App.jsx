import { useState } from "react";
import About from "./pages/About.jsx";
import Library from "./pages/Library.jsx";
import Transcribe from "./pages/Transcribe.jsx";

const TABS = [
  ["transcribe", "Transcribe"],
  ["library", "My Library"],
  ["about", "About"],
];

export default function App() {
  const [tab, setTab] = useState("transcribe");
  return (
    <>
      <header className="topbar">
        <h1 className="brand">LipiLens</h1>
        <nav>
          {TABS.map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? "tab active" : "tab"}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "transcribe" && <Transcribe />}
        {tab === "library" && <Library key="lib" />}
        {tab === "about" && <About />}
      </main>
      <footer className="muted small footer">
        AI-assisted, never AI-authoritative — verify every transcription.
      </footer>
    </>
  );
}
