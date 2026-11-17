/** Outline icons (lucide-style paths), so no icon package is needed. */
const PATHS = {
  home: 'M3 10.5 12 3l9 7.5V21H3z',
  layers: 'M12 3 2 8l10 5 10-5-10-5zM2 13l10 5 10-5',
  chat: 'M4 5h16v11H9l-5 4z',
  chart: 'M4 20V11M10 20V5M16 20v-6M2 20h20',
  upload: 'M12 16V4M6 10l6-6 6 6M4 20h16',
  play: 'M7 4l13 8-13 8z',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4',
  check: 'M5 12.5l4.5 4.5L19 7',
  checkCircle: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8 12.5l2.5 2.5L16 9.5',
  alert: 'M12 3 2 20h20zM12 10v4M12 17h.01',
  ban: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM5.6 5.6l12.8 12.8',
  plus: 'M12 5v14M5 12h14',
  x: 'M6 6l12 12M18 6 6 18',
  trash: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13',
  file: 'M14 3H6v18h12V7zM14 3v4h4',
  fileUp: 'M14 3H6v18h12V7zM14 3v4h4M12 17v-6M9 14l3-3 3 3',
  thumbUp: 'M7 11v9H4v-9zM7 11l4-8a2 2 0 0 1 3 2l-1 5h6a2 2 0 0 1 2 2l-2 7a2 2 0 0 1-2 1H7',
  image: 'M3 5h18v14H3zM9 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM21 16l-5-5-9 8',
  table: 'M3 5h18v14H3zM3 10h18M3 15h18M9 5v14',
  chevronDown: 'M6 9l6 6 6-6',
  arrowLeft: 'M19 12H5M11 6l-6 6 6 6',
  refresh: 'M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6',
  shield: 'M12 3l8 3v6c0 5.5-3.5 10-8 12-4.5-2-8-6.5-8-12V6z',
  spinner: 'M12 3a9 9 0 1 1-9 9',
  help: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4.5M12 17h.01',
  menu: 'M4 6h16M4 12h16M4 18h16',
  database: 'M12 3C7 3 3 5 3 7v10c0 2 4 4 9 4s9-2 9-4V7c0-2-4-4-9-4zM3 12c0 2 4 4 9 4s9-2 9-4',
  zap: 'M13 2 3 14h9l-1 8 10-12h-9z',
  barChart: 'M12 20V10M6 20V4M18 20v-6',
  eye: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  hash: 'M4 9h16M4 15h16M10 3v18M14 3v18',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  maximize: 'M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3',
  minus: 'M5 12h14',
  clock: 'M12 6v6l4 2M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z',
}

export function Icon({ name, size = 18, strokeWidth = 1.7, className, label }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
