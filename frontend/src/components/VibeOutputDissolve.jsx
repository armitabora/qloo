import { cloneElement, useEffect, useRef, useState } from 'react';
import {
  motion,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from 'motion/react';
import { useLenis } from 'lenis/react';

function smoothstep(t) {
  const x = Math.min(1, Math.max(0, t));
  return x * x * (3 - 2 * x);
}

const VIBE_CHROME =
  'isolate overflow-hidden border-t border-[var(--color-border)]';
const VIBE_INNER = 'relative z-10 mx-auto w-full max-w-2xl';

function DissolveRun({ atmosphere, children, reveal }) {
  const veilRef = useRef(null);
  const lenis = useLenis();
  const [revealedCovered, setRevealedCovered] = useState(true);

  const { scrollYProgress } = useScroll({
    target: veilRef,
    offset: ['start start', 'end end'],
  });

  const raw = useTransform(scrollYProgress, smoothstep);
  const eased = useSpring(raw, { stiffness: 260, damping: 44, mass: 0.5 });
  const scale = useTransform(eased, [0, 1], [1, 0.46]);
  const y = useTransform(eased, [0, 1], [0, -40]);
  const titleOpacity = useTransform(eased, [0.74, 1], [1, 0]);
  const backdropOpacity = useTransform(eased, [0.2, 0.92], [1, 0]);

  useEffect(() => {
    if (!lenis) return undefined;
    const id = window.requestAnimationFrame(() => lenis.resize());
    return () => window.cancelAnimationFrame(id);
  }, [lenis]);

  useMotionValueEvent(scrollYProgress, 'change', (progress) => {
    const nextCovered = progress < 0.68;
    setRevealedCovered((current) => (current === nextCovered ? current : nextCovered));
  });

  return (
    <div className="opening-stage vibe-stage relative">
      <div id="vibe-start" className="opening-anchor opening-anchor--start" />
      <div id="output" className="opening-anchor" />
      <section
        id="vibe"
        ref={veilRef}
        className={`intro-veil ${VIBE_CHROME}`}
        aria-labelledby="vibe-heading"
        inert={revealedCovered ? undefined : true}
      >
        <div className="sticky top-0 flex h-svh flex-col justify-center overflow-hidden px-6 py-16 md:px-10 md:py-20">
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={{ opacity: backdropOpacity }}
          >
            {atmosphere}
          </motion.div>
          <motion.div
            className="pointer-events-auto relative z-10"
            style={{
              scale,
              y,
              opacity: titleOpacity,
              transformOrigin: 'center 42%',
            }}
          >
            <div className={VIBE_INNER}>{children}</div>
          </motion.div>
        </div>
      </section>
      {reveal
        ? cloneElement(reveal, { inert: revealedCovered ? true : undefined })
        : null}
    </div>
  );
}

/**
 * Same dissolve as title → map: a pinned overlay fades while the next
 * scene sits sticky underneath. Used for vibe form → itinerary.
 */
export default function VibeOutputDissolve({
  active,
  atmosphere,
  children,
  reveal,
}) {
  const reduceMotion = useReducedMotion();
  const dissolve = active && reduceMotion !== true;

  if (!dissolve) {
    return (
      <>
        <section
          id="vibe"
          className={`relative ${VIBE_CHROME} flex min-h-svh flex-col justify-center px-6 py-16 md:px-10 md:py-20`}
          aria-labelledby="vibe-heading"
        >
          {atmosphere}
          <div className={VIBE_INNER}>{children}</div>
        </section>
        {reveal}
      </>
    );
  }

  return (
    <DissolveRun atmosphere={atmosphere} reveal={reveal}>
      {children}
    </DissolveRun>
  );
}
