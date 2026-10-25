import { useEffect, useState } from 'react';

const CYCLE_MS = 2200;

/**
 * Soft rounded compose box with a static lead-in plus a cycling example word,
 * inspired by Black Tomato's Feelings Engine placeholder pattern.
 */
export default function CyclingPromptField({
  id,
  leadIn,
  examples = [],
  value,
  onChange,
  error = false,
}) {
  const [index, setIndex] = useState(0);
  const [visible, setVisible] = useState(true);
  const [focused, setFocused] = useState(false);

  const showOverlay = !value && !focused && examples.length > 0;
  const current = examples[index % Math.max(examples.length, 1)] || '';

  useEffect(() => {
    if (!showOverlay || examples.length < 2) return undefined;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) return undefined;

    const id = window.setInterval(() => {
      setVisible(false);
      window.setTimeout(() => {
        setIndex((prev) => (prev + 1) % examples.length);
        setVisible(true);
      }, 220);
    }, CYCLE_MS);

    return () => window.clearInterval(id);
  }, [showOverlay, examples.length]);

  return (
    <div
      className={`relative rounded-2xl border px-5 py-4 transition-colors duration-200 ${
        error
          ? 'border-[var(--color-danger)]/60 bg-[var(--color-danger-bg)]'
          : focused
            ? 'border-[var(--color-fg)]/35 bg-[var(--color-fg)]/[0.06]'
            : 'border-[var(--color-fg)]/10 bg-[var(--color-fg)]/[0.04] hover:border-[var(--color-fg)]/20'
      }`}
    >
      {showOverlay && (
        <div
          className="pointer-events-none absolute inset-0 flex items-center px-5 text-lg text-[var(--color-fg)]/35"
          aria-hidden
        >
          <span className="shrink-0">{leadIn}&nbsp;</span>
          <span
            className="truncate transition-all duration-200 ease-out"
            style={{
              opacity: visible ? 1 : 0,
              transform: visible ? 'translateY(0)' : 'translateY(4px)',
            }}
          >
            {current}
          </span>
        </div>
      )}

      <label htmlFor={id} className="sr-only">
        {leadIn}
      </label>
      <input
        id={id}
        type="text"
        autoComplete="off"
        className="relative z-10 w-full bg-transparent text-lg text-[var(--color-fg)] outline-none placeholder:text-transparent"
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        aria-invalid={error || undefined}
      />
    </div>
  );
}
