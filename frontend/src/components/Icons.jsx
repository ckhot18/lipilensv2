const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export function IconUpload(props) {
  return (
    <svg {...base} {...props}>
      <path d="M7 17.5A4.5 4.5 0 0 1 7.6 8.6a5.5 5.5 0 0 1 10.5 1.4A3.75 3.75 0 0 1 17.5 17.5Z" />
      <path d="M12 15.5V10m0 0L9.8 12.2M12 10l2.2 2.2" />
    </svg>
  );
}

export function IconWand(props) {
  return (
    <svg {...base} {...props}>
      <path d="M5 19 16 8" />
      <path d="m14.5 5.5 1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1Z" />
      <path d="M6 6.5v3M4.5 8h3" />
    </svg>
  );
}

export function IconTextScan(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 8V6a2 2 0 0 1 2-2h2M20 8V6a2 2 0 0 0-2-2h-2M4 16v2a2 2 0 0 0 2 2h2M20 16v2a2 2 0 0 1-2 2h-2" />
      <path d="M8.5 12h7" />
    </svg>
  );
}

export function IconTranslate(props) {
  return (
    <svg {...base} {...props}>
      <path d="M3.5 6h8M7.5 4.2V6M9.8 6c-.4 3.4-2.6 6-6.3 7M5 9.4c1 2.2 2.9 3.7 5.2 4.3" />
      <path d="m12.5 20 3.6-9 3.6 9M14 17h4.2" />
    </svg>
  );
}

export function IconLayers(props) {
  return (
    <svg {...base} {...props}>
      <path d="m12 3.5 8 4-8 4-8-4Z" />
      <path d="m4 12 8 4 8-4" />
      <path d="m4 16.5 8 4 8-4" />
    </svg>
  );
}

export function IconChip(props) {
  return (
    <svg {...base} {...props}>
      <rect x="7" y="7" width="10" height="10" rx="2" />
      <path d="M10 3.5v3M14 3.5v3M10 17.5v3M14 17.5v3M3.5 10h3M3.5 14h3M17.5 10h3M17.5 14h3" />
    </svg>
  );
}

export function IconRoute(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="18" r="2.5" />
      <path d="M8.5 6h5a3.5 3.5 0 0 1 0 7h-3a3.5 3.5 0 0 0 0 7h5" />
    </svg>
  );
}

export function IconClock(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function IconFile(props) {
  return (
    <svg {...base} {...props}>
      <path d="M14 3.5H7.5a1.5 1.5 0 0 0-1.5 1.5v14a1.5 1.5 0 0 0 1.5 1.5h9a1.5 1.5 0 0 0 1.5-1.5V8Z" />
      <path d="M14 3.5V8h4.5" />
    </svg>
  );
}

export function IconShieldCheck(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.2 19 6v5.4c0 4.2-2.9 7.6-7 9.4-4.1-1.8-7-5.2-7-9.4V6Z" />
      <path d="m9.2 12 2 2 3.6-3.8" />
    </svg>
  );
}

export function IconCopy(props) {
  return (
    <svg {...base} {...props}>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M15 6.5V6a1.5 1.5 0 0 0-1.5-1.5h-7A1.5 1.5 0 0 0 5 6v7a1.5 1.5 0 0 0 1.5 1.5H8" />
    </svg>
  );
}

export function IconDownload(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 4v10" />
      <path d="m8 10.5 4 4 4-4" />
      <path d="M5 18.5h14" />
    </svg>
  );
}

export function IconMoon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M20.2 14.6A8.4 8.4 0 0 1 9.4 3.8a8.5 8.5 0 1 0 10.8 10.8Z" />
    </svg>
  );
}

export function IconSun(props) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      {...props}
    >
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2.6v2.2M12 19.2v2.2M21.4 12h-2.2M4.8 12H2.6M18.6 5.4l-1.6 1.6M7 17l-1.6 1.6M18.6 18.6 17 17M7 7 5.4 5.4" />
    </svg>
  );
}

export function IconArrowLeft(props) {
  return (
    <svg {...base} {...props}>
      <path d="M19 12H5.5" />
      <path d="m11 5.5-5.5 6.5 5.5 6.5" />
    </svg>
  );
}

export function IconArrowRight(props) {
  return (
    <svg {...base} {...props}>
      <path d="M5 12h13.5" />
      <path d="m13 5.5 5.5 6.5L13 18.5" />
    </svg>
  );
}

export function IconAlert(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 4.5 21 20H3Z" />
      <path d="M12 10v4M12 17h.01" />
    </svg>
  );
}

export function IconSearch(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </svg>
  );
}