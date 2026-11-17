/** Join class names, skipping falsy values (shadcn's `cn`, without tailwind-merge). */
export function cn(...parts) {
  return parts.flat().filter(Boolean).join(' ')
}

/** Minimal class-variance-authority: base classes + one class per chosen variant. */
export function cva(base, { variants = {}, defaultVariants = {} } = {}) {
  return (props = {}) =>
    cn(
      base,
      Object.keys(variants).map((key) => variants[key][props[key] ?? defaultVariants[key]]),
      props.className,
    )
}
