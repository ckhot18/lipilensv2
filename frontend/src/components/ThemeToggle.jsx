import { IconMoon, IconSun } from "./Icons.jsx";

export default function ThemeToggle({ dark, onToggle }) {
  return (
    <div className="themetoggle" role="group" aria-label="Colour theme">
      <button
        type="button"
        className={dark ? "themebtn on moon" : "themebtn"}
        onClick={() => !dark && onToggle()}
        aria-pressed={!dark}
        aria-label="Light mode"
        title="Light mode"
      >
        <IconMoon style={{ width: 13, height: 13 }} />
      </button>
      <button
        type="button"
        className={dark ? "themebtn sun" : "themebtn on sun"}
        onClick={() => dark && onToggle()}
        aria-pressed={dark}
        aria-label="Dark mode"
        title="Dark mode"
      >
        <IconSun style={{ width: 13, height: 13 }} />
      </button>
    </div>
  );
}