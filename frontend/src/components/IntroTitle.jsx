import { useRef, useState } from 'react';
import {
  motion,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from 'motion/react';
import { CaretDown } from '@phosphor-icons/react';
import { BlurFade } from '@/components/ui/blur-fade';
import { DotPattern } from '@/components/ui/dot-pattern';
import DynamicText from '@/components/kokonutui/dynamic-text';

const TASTE_WORDS = ['music', 'films', 'moods'];

function Reveal({ calm, delay = 0, blur = '8px', className, children }) {
  if (calm) return <div className={className}>{children}</div>;

  const soft = blur !== '0px';
  return (
    <BlurFade
      delay={delay}
      duration={0.45}
      offset={soft ? 12 : 8}
      blur={blur}
      className={className}
      variant={
        soft
          ? undefined
          : {
              hidden: { y: 8, opacity: 0 },
              visible: { y: 0, opacity: 1 },
            }
      }
    >
      {children}
    </BlurFade>
  );
}

function PopLine({ delay, calm, children }) {
  if (calm) {
    return <span className="block">{children}</span>;
  }

  return (
    <motion.span
      className="block origin-center"
      initial={{ opacity: 0, scale: 0.64, y: 56 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{
        type: 'spring',
        stiffness: 340,
        damping: 18,
        mass: 0.78,
        delay,
      }}
    >
      {children}
    </motion.span>
  );
}

function smoothstep(t) {
  const x = Math.min(1, Math.max(0, t));
  return x * x * (3 - 2 * x);
}

export default function IntroTitle({ children }) {
  const veilRef = useRef(null);
  const reduceMotion = useReducedMotion();
  const calm = reduceMotion === true;
  const [hintGone, setHintGone] = useState(false);
  const [mapCovered, setMapCovered] = useState(true);
  // Spans exactly the pinned run: 0 when the title locks, 1 when the map takes over.
  const { scrollYProgress } = useScroll({
    target: veilRef,
    offset: ['start start', 'end end'],
  });

  const raw = useTransform(scrollYProgress, smoothstep);
  const eased = useSpring(raw, { stiffness: 260, damping: 44, mass: 0.5 });
  const scale = useTransform(eased, [0, 1], [1, 0.46]);
  const y = useTransform(eased, [0, 1], [0, -40]);
  const copyOpacity = useTransform(eased, [0.34, 0.72], [1, 0]);
  const hintOpacity = useTransform(eased, [0.06, 0.32], [1, 0]);
  const fieldOpacity = useTransform(eased, [0.18, 0.66], [1, 0]);
  const titleOpacity = useTransform(eased, [0.74, 1], [1, 0]);
  const backdropOpacity = useTransform(eased, [0.2, 0.92], [1, 0]);

  useMotionValueEvent(scrollYProgress, 'change', (progress) => {
    if (calm) {
      setHintGone(false);
      setMapCovered(false);
      return;
    }
    const nextHint = progress > 0.3;
    const nextCovered = progress < 0.68;
    setHintGone((current) => (current === nextHint ? current : nextHint));
    setMapCovered((current) => (current === nextCovered ? current : nextCovered));
  });

  const scrollStyle = calm
    ? undefined
    : { scale, y, opacity: titleOpacity, transformOrigin: 'center 42%' };

  return (
    <div className={calm ? 'relative' : 'opening-stage relative'}>
      {calm ? null : <div id="city" className="opening-anchor" />}
      <section
        id="intro"
        ref={calm ? undefined : veilRef}
        aria-labelledby="intro-heading"
        className={calm ? 'intro-ocean-calm relative' : 'intro-veil'}
      >
        <div
          className={
            calm
              ? 'relative flex min-h-[100svh] items-center justify-center overflow-hidden px-6 py-20'
              : 'sticky top-0 flex h-svh items-center justify-center overflow-hidden px-6'
          }
        >
          <motion.div
            aria-hidden="true"
            className={calm ? 'hidden' : 'intro-ocean pointer-events-none absolute inset-0'}
            style={calm ? undefined : { opacity: backdropOpacity }}
          />

          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={calm ? undefined : { opacity: fieldOpacity }}
          >
            <DotPattern
              width={28}
              height={28}
              cr={0.65}
              className="text-[var(--color-fg)]/25 [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_72%)]"
            />
          </motion.div>

          <motion.div
            style={scrollStyle}
            className="pointer-events-auto relative z-10 flex w-full max-w-3xl flex-col items-center text-center"
          >
          <div
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[28rem] w-[28rem] -translate-x-1/2 -translate-y-[58%] rounded-full bg-[radial-gradient(circle,color-mix(in_oklch,var(--antique-gold)_22%,transparent),transparent_68%)]"
          />
          <motion.div style={calm ? undefined : { opacity: copyOpacity }}>
            <Reveal calm={calm} delay={0.08} blur="0px">
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--color-fg)]/55 uppercase">
                Taste-intelligent travel
              </p>
            </Reveal>
          </motion.div>

          <h1
            id="intro-heading"
            className="mt-5 text-[clamp(4.8rem,12vw,8.5rem)] font-extrabold leading-[0.82] tracking-[-0.045em] text-[var(--color-fg)]"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            <PopLine calm={calm} delay={0.04}>
              Vibe
            </PopLine>
            <PopLine calm={calm} delay={0.12}>
              Guide
            </PopLine>
          </h1>

          <motion.div style={calm ? undefined : { opacity: copyOpacity }} className="mt-8 max-w-2xl">
            <Reveal calm={calm} delay={0.22}>
              <p className="sr-only">
                VibeGuide is a taste-intelligent travel concierge. Generic guides give everyone the
                same list. VibeGuide reads your music, films, and moods, then builds a city day that
                feels like you.
              </p>
              <p aria-hidden="true" className="text-base leading-relaxed text-[var(--color-muted)] md:text-lg">
                <span className="block">Generic guides give everyone the same list.</span>
                <span className="mt-1.5 block">
                  VibeGuide reads your{' '}
                  <DynamicText
                    mode="morph"
                    words={TASTE_WORDS}
                    interval={2100}
                    className="font-semibold text-[var(--color-accent)]"
                  />{' '}
                  and builds a day that feels like you.
                </span>
              </p>
            </Reveal>
          </motion.div>

          <motion.div
            style={calm ? undefined : { opacity: hintOpacity }}
            className="mt-10"
            aria-hidden={hintGone || undefined}
          >
            <Reveal calm={calm} delay={0.34} blur="0px">
              <a
                href="#city"
                tabIndex={hintGone ? -1 : undefined}
                className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-[var(--color-fg)]/15 bg-[var(--color-fg)]/10 px-5 text-sm font-semibold text-[var(--color-fg)] transition-colors duration-200 hover:bg-[var(--color-fg)]/15"
              >
                Choose a city
                <CaretDown size={16} weight="bold" aria-hidden="true" />
              </a>
            </Reveal>
          </motion.div>
          </motion.div>
        </div>
      </section>

      <section
        id={calm ? 'city' : undefined}
        className={calm ? 'relative bg-[var(--velvet-deep)]' : 'sticky top-0 z-0 h-svh overflow-hidden bg-[var(--velvet-deep)]'}
        aria-label="Choose a city"
        inert={!calm && mapCovered ? true : undefined}
      >
        {children}
      </section>
    </div>
  );
}
