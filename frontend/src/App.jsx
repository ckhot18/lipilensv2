import { useCallback, useEffect, useState } from "react";
import About from "./pages/About.jsx";
import Home from "./pages/Home.jsx";
import Library from "./pages/Library.jsx";
import Transcribe from "./pages/Transcribe.jsx";
import { IconLeaf, IconGithub } from "./components/Icons.jsx";
import { health } from "./api/client";

const ROUTES = [
  { path: "/", tab: "home", label: "Home" },
  { path: "/transcribe", tab: "transcribe", label: "Transcribe" },
  { path: "/library", tab: "library", label: "Library" },
  { path: "/about", tab: "about", label: "About" },
];

function getTabFromPath(pathname) {
  const clean = (pathname || "").toLowerCase().replace(/\/$/, "") || "/";
  if (clean === "" || clean === "/") return "home";
  if (clean.startsWith("/transcribe")) return "transcribe";
  if (clean.startsWith("/library")) return "library";
  if (clean.startsWith("/about")) return "about";
  return "home";
}

function getPathFromTab(tab) {
  if (tab === "transcribe") return "/transcribe";
  if (tab === "library") return "/library";
  if (tab === "about") return "/about";
  return "/";
}

export default function App() {
  const [tab, setTab] = useState(() => getTabFromPath(window.location.pathname));
  const [healthStatus, setHealthStatus] = useState(null);
  const [pendingFile, setPendingFile] = useState(null);
  const [runToken, setRunToken] = useState(0);

  // Sync tab with browser URL history
  useEffect(() => {
    function onPopState() {
      setTab(getTabFromPath(window.location.pathname));
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    let cancelled = false;
    health()
      .then((res) => !cancelled && setHealthStatus(res))
      .catch(() => !cancelled && setHealthStatus({ status: "down" }));
    return () => {
      cancelled = true;
    };
  }, []);

  const navigate = useCallback((nextTab) => {
    const targetPath = getPathFromTab(nextTab);
    if (window.location.pathname !== targetPath) {
      window.history.pushState({}, "", targetPath);
    }
    setTab(nextTab);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  function startWith(file) {
    setPendingFile(file);
    setRunToken((n) => n + 1);
    navigate("transcribe");
  }

  const clearPending = useCallback(() => setPendingFile(null), []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <a
            href="/"
            className="brandwrap"
            onClick={(e) => {
              e.preventDefault();
              navigate("home");
            }}
          >
            <span className="brand-leaf" aria-hidden="true">
              <IconLeaf style={{ width: 24, height: 24 }} />
            </span>
            <span className="brand-text">LipiLens</span>
          </a>

          <nav className="topnav" aria-label="Primary">
            {ROUTES.map((route) => (
              <a
                key={route.tab}
                href={route.path}
                className={tab === route.tab ? "tab active" : "tab"}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(route.tab);
                }}
                aria-current={tab === route.tab ? "page" : undefined}
              >
                {route.label}
              </a>
            ))}
          </nav>

          <div className="topright">
            <a
              href="https://github.com/ckhot18/lipilensv2"
              target="_blank"
              rel="noreferrer"
              className="github-link"
              aria-label="View LipiLens on GitHub"
            >
              <IconGithub style={{ width: 18, height: 18 }} />
              <span>GitHub</span>
              <span className="ext" aria-hidden="true">
                &#8599;
              </span>
            </a>
            {tab === "home" && (
              <button
                type="button"
                className="btn-header-cta"
                onClick={() => navigate("transcribe")}
              >
                Start transcribing
              </button>
            )}
          </div>
        </div>
      </header>

      {healthStatus && healthStatus.status !== "ok" && (
        <p className="health-banner" role="status" aria-live="polite">
          {healthStatus.reason || "Backend unreachable — the API is not responding."}
        </p>
      )}

      <main className="content-container">
        {tab === "home" && (
          <Home
            onStart={startWith}
            onNavigateTranscribe={() => navigate("transcribe")}
            onNavigateLibrary={() => navigate("library")}
          />
        )}
        {tab === "transcribe" && (
          <Transcribe
            key={runToken}
            autoFile={pendingFile}
            onAutoFileConsumed={clearPending}
            onOpenLibrary={() => navigate("library")}
          />
        )}
        {tab === "library" && (
          <Library
            initialQuery=""
            onNavigateTranscribe={() => navigate("transcribe")}
          />
        )}
        {tab === "about" && (
          <About onExploreLibrary={() => navigate("library")} />
        )}
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-left">
            <span className="footer-brand">
              <IconLeaf style={{ width: 14, height: 14, marginRight: 6 }} />
              <strong>LipiLens</strong>
            </span>
            <span className="footer-tagline">
              Preserving historical Modi manuscripts through AI-assisted
              transcription &amp; human verification.
            </span>
          </div>
          <div className="footer-right">
            <a
              href="https://github.com/ckhot18/lipilensv2"
              target="_blank"
              rel="noreferrer"
              className="footer-link"
            >
              GitHub repository
            </a>
            <button
              type="button"
              className="footer-btn"
              onClick={() => navigate("about")}
            >
              About &amp; Principles
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
