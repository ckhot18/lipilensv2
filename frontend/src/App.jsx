import { useEffect, useState } from "react";
import About from "./pages/About.jsx";
import Home from "./pages/Home.jsx";
import Library from "./pages/Library.jsx";
import Transcribe from "./pages/Transcribe.jsx";

const TABS = [
  ["home", "Home"],
  ["library", "Library"],
  ["about", "About"],
];

export default function App() {
  const [tab, setTab] = useState("home");
  const [dark, setDark] = useState(
    () => localStorage.getItem("lipilens-theme") === "dark"
  );
  const [globalQuery, setGlobalQuery] = useState("");
  const [searchBox, setSearchBox] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("lipilens-theme", dark ? "dark" : "light");
  }, [dark]);

  function go(next, query) {
    if (query !== undefined) setGlobalQuery(query);
    setTab(next);
  }

  function submitSearch(e) {
    e.preventDefault();
    go("library", searchBox);
  }

  return (
    <>
      <header className="topbar">
        <div className="brandwrap">
          <div className="brandmark" aria-hidden="true">✦</div>
          <h1 className="brand">
            Lipi<span className="lens">Lens</span>
          </h1>
        </div>
        <nav>
          {TABS.map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? "tab active" : "tab"}
              onClick={() => go(key)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="topright">
          <form onSubmit={submitSearch}>
            <input
              className="hsearch"
              value={searchBox}
              onChange={(e) => setSearchBox(e.target.value)}
              placeholder="Search manuscripts, places, keywords…"
            />
          </form>
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
        <main className="full">
          {tab === "home" && <Home go={go} />}
          {tab === "transcribe" && <Transcribe />}
          {tab === "library" && <Library key={globalQuery} initialQuery={globalQuery} />}
          {tab === "about" && <About />}
        </main>
      </div>

      <footer className="footer">
        <span>
          <strong>✦ LipiLens</strong>{" "}
          <span className="muted">Ancient scripts. New possibilities.</span>
        </span>
        <span className="muted small">
          <span className="flink" onClick={() => go("about")}>Research</span> · Built with ♥ for a more accessible past.
        </span>
      </footer>
    </>
  );
}
