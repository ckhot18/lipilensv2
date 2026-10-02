import { useCallback, useEffect, useState } from "react";
import About from "./pages/About.jsx";
import Home from "./pages/Home.jsx";
import Library from "./pages/Library.jsx";
import Transcribe from "./pages/Transcribe.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import { health } from "./api/client";

const TABS = [
  ["home", "Home"],
  ["transcribe", "Transcribe"],
  ["library", "Library"],
  ["about", "About"],
];

const THEME_KEY = "lipilens-theme";

function initialTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "dark" || stored === "light") return stored === "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export default function App() {
  const [tab, setTab] = useState("home");
  const [dark, setDark] = useState(initialTheme);
  const [searchBox, setSearchBox] = useState("");
  const [query, setQuery] = useState("");
  const [healthStatus, setHealthStatus] = useState(null);
  const [pendingFile, setPendingFile] = useState(null);
  const [runToken, setRunToken] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    let cancelled = false;
    health()
      .then((res) => !cancelled && setHealthStatus(res))
      .catch(() => !cancelled && setHealthStatus({ status: "down" }));
    return () => {
      cancelled = true;
    };
  }, []);

  const go = useCallback((next, nextQuery) => {
    if (nextQuery !== undefined) setQuery(nextQuery);
    setTab(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  function startWith(file) {
    setPendingFile(file);
    setRunToken((n) => n + 1);
    go("transcribe");
  }

  const clearPending = useCallback(() => setPendingFile(null), []);

  function submitSearch(event) {
    event.preventDefault();
    go("library", searchBox);
  }

  return (
    <>
      <header className="topbar">
        <div className="brandwrap">
          <span className="brandmark" aria-hidden="true">
            &#9670;
          </span>
          <h1 className="brand">
            Lipi<span className="lens">Lens</span>
          </h1>
        </div>

        <nav className="topnav" aria-label="Primary">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={tab === key ? "tab active" : "tab"}
              onClick={() => go(key)}
              aria-current={tab === key ? "page" : undefined}
            >
              {label}
            </button>
          ))}
        </nav>

        <div className="topright">
          <form onSubmit={submitSearch} role="search">
            <input
              className="hsearch"
              type="search"
              value={searchBox}
              onChange={(e) => setSearchBox(e.target.value)}
              placeholder="Search manuscripts…"
              aria-label="Search the manuscript library"
            />
          </form>
          <ThemeToggle dark={dark} onToggle={() => setDark((d) => !d)} />
        </div>
      </header>

      {healthStatus && healthStatus.status !== "ok" && (
        <p className="health-banner" role="status" aria-live="polite">
          {healthStatus.reason || "Backend unreachable — the API is not responding."}
        </p>
      )}

      <div className="body">
        <main className="full">
          {tab === "home" && <Home onStart={startWith} />}
          {tab === "transcribe" && (
            <Transcribe
              key={runToken}
              autoFile={pendingFile}
              onAutoFileConsumed={clearPending}
              onOpenLibrary={() => go("library")}
            />
          )}
          {tab === "library" && <Library key={query} initialQuery={query} />}
          {tab === "about" && <About />}
        </main>
      </div>

      <footer className="footer">
        <span>
          <strong>LipiLens</strong> <span className="muted">Ancient scripts. New possibilities.</span>
        </span>
        <span className="muted">
          <button type="button" className="toolbtn" onClick={() => go("about")}>
            Research &amp; method
          </button>
        </span>
      </footer>
    </>
  );
}