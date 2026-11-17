/** Line-art illustrations: Argus, the watchful eye whose pupil is the brand red, and small step drawings. */

export function HeroArt() {
  const pages = [[60, 78], [40, 252], [118, 388], [1040, 56], [1066, 236], [986, 396]]
  return (
    <svg aria-hidden="true" viewBox="0 0 1200 520" className="pointer-events-none absolute top-10 left-1/2 h-[520px] w-[1200px] max-w-none -translate-x-1/2 opacity-45">
      <g fill="none" stroke="#3A3734">
        <path d="M330 260 Q600 70 870 260 Q600 450 330 260 Z" />
        <path d="M370 260 Q600 105 830 260 Q600 415 370 260 Z" stroke="#2E2C2A" />
        <circle cx="600" cy="260" r="118" />
        <circle cx="600" cy="260" r="92" stroke="#2E2C2A" />
        <circle cx="600" cy="260" r="64" stroke="#2E2C2A" strokeDasharray="2 6" />
        <path d="M600 142V120M600 378v22M482 260h-22M718 260h22" stroke="#57534C" />
        <path d="M330 260 L120 120M330 260 L90 300M330 260 L170 430M870 260 L1080 110M870 260 L1110 290M870 260 L1030 440" stroke="#2A2827" strokeDasharray="3 5" />
      </g>
      <g className="anim-look">
        <circle cx="600" cy="260" r="26" fill="#810100" opacity=".55" />
        <circle cx="610" cy="250" r="5" fill="#EDEBDD" opacity=".5" />
      </g>
      {pages.map(([x, y]) => <rect key={`${x}-${y}`} x={x} y={y} width="96" height="124" rx="4" fill="#1E1C1C" stroke="#3A3734" />)}
      <g stroke="#3A3734" strokeWidth="3" strokeLinecap="round">
        <path d="M74 100h60M74 112h52M74 124h66M54 274h60M54 286h44M132 410h60M132 422h52M1054 78h60M1054 90h40M1080 258h60M1080 270h52M1000 418h60M1000 430h48" />
      </g>
      <g strokeWidth="3" strokeLinecap="round">
        <path d="M74 136h44" stroke="#3F7A4F" /><path d="M54 298h58" stroke="#810100" />
        <path d="M1054 102h56" stroke="#3F7A4F" /><path d="M1080 282h36" stroke="#B9892A" />
      </g>
    </svg>
  )
}

export function GridBackdrop() {
  return (
    <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full">
      <defs>
        <pattern id="grid-s" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" fill="none" stroke="#232121" /></pattern>
        <pattern id="grid-l" width="192" height="192" patternUnits="userSpaceOnUse"><path d="M192 0H0V192" fill="none" stroke="#2A2827" /></pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid-s)" />
      <rect width="100%" height="100%" fill="url(#grid-l)" />
    </svg>
  )
}

const box = (d, stroke = '#3A3734') => <path d={d} fill="none" stroke={stroke} />

/** One small drawing per checking step. */
export const STEP_ART = {
  retrieve: (
    <svg aria-hidden="true" viewBox="0 0 220 96" className="h-24 w-full">
      <g fill="none" stroke="#3A3734"><rect x="8" y="10" width="60" height="76" rx="4" /><rect x="80" y="10" width="60" height="76" rx="4" /><rect x="152" y="10" width="60" height="76" rx="4" stroke="#57534C" /></g>
      <g stroke="#3A3734" strokeWidth="3" strokeLinecap="round"><path d="M18 28h40M18 40h32M90 28h40M90 40h28M162 28h40M162 52h34" /><path d="M162 40h40" stroke="#EDEBDD" /></g>
      <g className="anim-scan"><circle cx="182" cy="26" r="14" fill="none" stroke="#EDEBDD" strokeWidth="1.5" /><path d="M192 36l8 8" stroke="#EDEBDD" strokeWidth="1.5" strokeLinecap="round" /></g>
    </svg>
  ),
  draft: (
    <svg aria-hidden="true" viewBox="0 0 220 96" className="h-24 w-full">
      {box('M20 30q0-14 14-14M20 30h14v14H20zM48 30q0-14 14-14M48 30h14v14H48z', '#57534C')}
      <g strokeWidth="3" strokeLinecap="round"><path d="M86 26h120M86 40h96" stroke="#3A3734" /><path d="M20 64h120" stroke="#EDEBDD" /><path d="M20 78h80" stroke="#3A3734" /></g>
      <rect x="150" y="56" width="58" height="28" rx="14" fill="none" stroke="#810100" /><path d="M162 70h34" stroke="#810100" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  check: (
    <svg aria-hidden="true" viewBox="0 0 220 96" className="h-24 w-full">
      <path d="M110 12v70M60 82h100M40 30h140" stroke="#57534C" strokeWidth="2" strokeLinecap="round" />
      <path d="M40 30l-16 32h32zM180 30l-16 32h32z" fill="none" stroke="#3A3734" strokeWidth="1.5" />
      <path d="M24 62q16 12 32 0" fill="none" stroke="#3F7A4F" strokeWidth="2" /><path d="M164 62q16 12 32 0" fill="none" stroke="#3A3734" strokeWidth="2" />
      <circle cx="110" cy="12" r="4" fill="#810100" />
    </svg>
  ),
  decide: (
    <svg aria-hidden="true" viewBox="0 0 220 96" className="h-24 w-full">
      <path d="M110 8l40 14v26c0 22-16 36-40 42-24-6-40-20-40-42V22z" fill="none" stroke="#57534C" strokeWidth="2" strokeLinejoin="round" />
      <path d="M93 48l12 12 22-24" fill="none" stroke="#8DB87A" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M24 48h34M162 48h34" stroke="#3A3734" strokeWidth="3" strokeLinecap="round" />
    </svg>
  ),
  upload: (
    <svg aria-hidden="true" width="220" height="120" viewBox="0 0 220 120">
      <g className="anim-float">
        <rect x="62" y="6" width="60" height="78" rx="6" fill="#1E1C1C" stroke="#57534C" transform="rotate(-8 92 45)" />
        <g transform="rotate(6 128 41)">
          <rect x="98" y="2" width="60" height="78" rx="6" fill="#211F1F" stroke="#A8A496" />
          <path d="M112 22h34M112 32h26M112 42h30" stroke="#57534C" strokeWidth="3" strokeLinecap="round" />
          <path d="M112 52h22" stroke="#810100" strokeWidth="3" strokeLinecap="round" />
        </g>
      </g>
      <path d="M60 104h100" stroke="#3A3734" strokeWidth="2" strokeLinecap="round" />
      <path d="M110 92v-18M102 82l8-8 8 8" fill="none" stroke="#EDEBDD" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
}
