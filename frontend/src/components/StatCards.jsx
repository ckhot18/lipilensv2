import { IconChip, IconLayers, IconRoute, IconTextScan, IconWand } from "./Icons.jsx";

function fmt(ms) {
  if (ms == null) return "—";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export default function StatCards({
  pipeline,
  model,
  mode,
  lines,
  restoreMs,
  readMs,
}) {
  const rows = [
    [IconLayers, "Restoration Pipeline", pipeline || "—"],
    [IconWand, "Restoration (CPU)", fmt(restoreMs)],
    [IconChip, "AI Read (GPU)", fmt(readMs)],
    [IconChip, "Model", model || "—"],
    [IconRoute, "Inference", mode || "—"],
    [
      IconTextScan,
      "Lines Read",
      lines ? `${lines} line${lines === 1 ? "" : "s"}` : "—",
    ],
  ];
  return (
    <div className="statgrid">
      {rows.map(([Icon, label, value]) => (
        <div key={label} className="stat">
          <span className="stat-ic">
            <Icon />
          </span>
          <span>
            <span className="stat-label">{label}</span>
            <span className="stat-value" title={value}>
              {value}
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}