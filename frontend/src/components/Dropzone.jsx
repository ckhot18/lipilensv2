import { useRef, useState } from "react";
import { useObjectUrl } from "../lib/useObjectUrl.js";
import { IconUpload } from "./Icons.jsx";

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 20 * 1024 * 1024;

function validateImage(file) {
  if (!file) return null;
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
    return "Please choose a JPG, PNG or WEBP image.";
  }
  if (file.size > MAX_BYTES) return "File exceeds the 20 MB limit.";
  return null;
}

export default function Dropzone({ initialFile = null, onFile, compact = false }) {
  const [over, setOver] = useState(false);
  const [problem, setProblem] = useState("");
  const [picked, select] = useObjectUrl(initialFile);
  const input = useRef(null);

  function pick(file) {
    const found = validateImage(file);
    setProblem(found || "");
    if (found) return;
    select(file);
    onFile(file);
  }

  function open(event) {
    event.stopPropagation();
    input.current?.click();
  }

  return (
    <div
      className={over ? "dropzone over" : "dropzone"}
      onClick={() => input.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          input.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        pick(e.dataTransfer.files?.[0]);
      }}
      role="button"
      tabIndex={0}
      aria-label="Upload a manuscript image"
    >
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        className="dz-sr"
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      {picked ? (
        <>
          <img className="dz-preview" src={picked.url} alt={`Selected file: ${picked.file.name}`} />
          <p className="dz-filename">{picked.file.name}</p>
          <p className="dz-sub">
            {(picked.file.size / 1024).toFixed(0)} KB · click to replace
          </p>
        </>
      ) : (
        <>
          <span className="cloudicon">
            <IconUpload style={{ width: 34, height: 34, strokeWidth: 1.4 }} />
          </span>
          <p className="dz-title">
            {compact ? "Upload a manuscript" : "Upload your manuscript"}
          </p>
          <p className="dz-sub">Drag &amp; drop an image here</p>
          <p className="dz-or">or</p>
          <button type="button" className="btn sm" onClick={open}>
            Browse files
          </button>
        </>
      )}

      <p className="dz-meta">JPG · PNG · WEBP &nbsp;|&nbsp; Max 20 MB</p>

      {problem && (
        <p className="notice err" role="alert" style={{ margin: "12px 0 0" }}>
          {problem}
        </p>
      )}
    </div>
  );
}