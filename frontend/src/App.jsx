import { useEffect, useState } from "react";
import About from "./pages/About.jsx";
import Library from "./pages/Library.jsx";
import Transcribe from "./pages/Transcribe.jsx";

const TABS = [
  ["transcribe", "Transcribe", "⌂"],
  ["library", "My Library", "▤"],
  ["about", "About", "ⓘ"],
];

export default function App() {
  const [tab, setTab] = useState("transcribe");
  const [dark, setDark] = useState(
    () => localStorage.getItem("lipilens-theme") === "dark"
  );

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("lipilens-theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <>
      <header className="topbar">
        <div className="brandwrap">
          <div className="brandmark" aria-hidden="true">✒</div>
          <div>
            <h1 className="brand">
              Lipi<span className="lens">Lens</span>
            </h1>
            <p className="tagline">Ancient Scripts. New Possibilities.</p>
          </div>
        </div>
        <div className="topright">
          <span className="motto">Preserve &nbsp;·&nbsp; Transcribe &nbsp;·&nbsp; Make History Accessible</span>
          <button
            className="iconbtn"
            onClick={() => setDark((d) => !d)}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? "☀" : "☾"}
          </button>
        </div>
      </header>

      <div className="body">
        <aside className="sidebar">
          <nav>
            {TABS.map(([key, label, ico]) => (
              <button
                key={key}
                className={tab === key ? "navbtn active" : "navbtn"}
                onClick={() => setTab(key)}
              >
                <span className="ico">{ico}</span> {label}
              </button>
            ))}
          </nav>
          <div className="quote">
            <p className="marathi">“भूतकाळ जपणे,<br />भविष्य घडवणे.”</p>
            <p className="small">Preserve the past, for a wiser future.</p>
          </div>
        </aside>

        <main>
          {tab === "transcribe" && <Transcribe />}
          {tab === "library" && <Library key="lib" />}
          {tab === "about" && <About />}
        </main>
      </div>

      <footer className="footer">
        <span>
          <strong>LipiLens</strong> <span className="muted">v0.1.0</span>
        </span>
        <span className="muted">Built for India&apos;s heritage ♥ &nbsp;|&nbsp; Open Source</span>
      </footer>
    </>
  );
}
