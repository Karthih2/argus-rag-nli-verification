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
  spinner: 'M12 3a9 9 0 1 1-9 9',
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
