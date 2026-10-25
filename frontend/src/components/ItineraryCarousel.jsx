import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValue, useReducedMotion } from 'motion/react';
import { CaretLeft, CaretRight } from '@phosphor-icons/react';
import { upgradeImageUrl } from '../lib/imageUrl';

function SleeveFace({ stop, priority = false }) {
  const src = upgradeImageUrl(stop.image_url);
  const [failed, setFailed] = useState(false);

  if (src && !failed) {
    return (
      <img
        src={src}
        alt=""
        className="itinerary-sleeve__img"
        draggable={false}
        decoding="async"
        fetchPriority={priority ? 'high' : 'low'}
        onError={() => setFailed(true)}
      />
    );
  }

  const initial = (stop.venue || '?').trim().charAt(0).toUpperCase() || '?';

  return (
    <div className="itinerary-sleeve__fallback" aria-hidden>
      <span className="itinerary-sleeve__phase">{stop.phase}</span>
      <span className="itinerary-sleeve__initial">{initial}</span>
      <span className="itinerary-sleeve__venue">{stop.venue}</span>
    </div>
  );
}

/**
 * Centered sleeve carousel. Track motion is button-driven only (no wheel/drag).
 * Featured copy below tracks the active stop.
 */
export default function ItineraryCarousel({ itinerary, onReset }) {
  const stops = itinerary?.stops ?? [];
  const [activeIndex, setActiveIndex] = useState(0);
  const [hoverSide, setHoverSide] = useState(null);
  const [isDesktopNav, setIsDesktopNav] = useState(false);
  const viewportRef = useRef(null);
  const cursorX = useMotionValue(0);
  const cursorY = useMotionValue(0);
  const reduceMotion = useReducedMotion();

  const count = stops.length;
  const active = stops[activeIndex] ?? null;

  useEffect(() => {
    setActiveIndex(0);
  }, [itinerary?.city, count]);

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)');
    const sync = () => setIsDesktopNav(mq.matches);
    sync();
    mq.addEventListener('change', sync);
    return () => mq.removeEventListener('change', sync);
  }, []);

  const goTo = useCallback(
    (next) => {
      if (count === 0) return;
      const wrapped = ((next % count) + count) % count;
      setActiveIndex(wrapped);
    },
    [count]
  );

  const goPrev = useCallback(() => goTo(activeIndex - 1), [activeIndex, goTo]);
  const goNext = useCallback(() => goTo(activeIndex + 1), [activeIndex, goTo]);

  useEffect(() => {
    const onKey = (e) => {
      const root = viewportRef.current;
      if (!root) return;
      if (!root.contains(document.activeElement) && document.activeElement !== root) {
        return;
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goPrev();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        goNext();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [goPrev, goNext]);

  if (!active || count === 0) return null;

  const affinity =
    typeof active.affinity === 'number'
      ? `${Math.round(active.affinity * 100)}% match`
      : null;

  return (
    <div
      className="itinerary-carousel"
      style={{ '--itinerary-index': activeIndex }}
    >
      <header className="mx-auto max-w-2xl px-6 md:px-10">
        <h2
          id="output-heading"
          className="text-[clamp(1.5rem,3.2vw,2.25rem)] font-bold tracking-[-0.03em] text-[var(--ink)]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          Your vibe in {itinerary.city}
        </h2>
        {itinerary.is_fallback && (
          <p className="mt-2 text-sm text-[var(--ink-muted)]">
            Showing a fallback day. Live Qloo recommendations were unavailable for this run.
          </p>
        )}
      </header>

      <div
        ref={viewportRef}
        className="itinerary-carousel__viewport"
        tabIndex={0}
        role="region"
        aria-roledescription="carousel"
        aria-label={`Itinerary stops in ${itinerary.city}`}
        onPointerMove={(e) => {
          if (!isDesktopNav || reduceMotion) return;
          cursorX.set(e.clientX);
          cursorY.set(e.clientY);
        }}
      >
        <div className="itinerary-carousel__stage">
          <div className="itinerary-carousel__track">
            {stops.map((stop, idx) => {
              const isActive = idx === activeIndex;
              return (
                <article
                  key={`${stop.phase}-${stop.venue}-${idx}`}
                  className={`itinerary-carousel__slide${isActive ? ' is-active' : ''}`}
                  aria-hidden={!isActive}
                  aria-label={`${stop.phase}: ${stop.venue}`}
                  data-index={idx}
                >
                  <button
                    type="button"
                    className="itinerary-sleeve"
                    onClick={() => goTo(idx)}
                    tabIndex={isActive ? 0 : -1}
                  >
                    <SleeveFace stop={stop} priority={isActive} />
                  </button>
                </article>
              );
            })}
          </div>
        </div>

        {isDesktopNav && (
          <div className="itinerary-carousel__hit-areas">
            <button
              type="button"
              className="itinerary-carousel__hit itinerary-carousel__hit--prev"
              aria-label="Previous stop"
              onClick={goPrev}
              onMouseEnter={() => setHoverSide('prev')}
              onMouseLeave={() => setHoverSide(null)}
            />
            <button
              type="button"
              className="itinerary-carousel__hit itinerary-carousel__hit--next"
              aria-label="Next stop"
              onClick={goNext}
              onMouseEnter={() => setHoverSide('next')}
              onMouseLeave={() => setHoverSide(null)}
            />
          </div>
        )}

        {isDesktopNav && !reduceMotion && (
          <motion.div
            className="itinerary-carousel__cursor"
            style={{
              left: cursorX,
              top: cursorY,
              opacity: hoverSide ? 1 : 0,
            }}
            aria-hidden
          >
            {hoverSide === 'prev' ? (
              <CaretLeft size={40} weight="bold" />
            ) : (
              <CaretRight size={40} weight="bold" />
            )}
          </motion.div>
        )}

        {!isDesktopNav && (
          <div className="itinerary-carousel__mobile-nav">
            <button
              type="button"
              className="itinerary-carousel__mobile-btn"
              aria-label="Previous stop"
              onClick={goPrev}
            >
              <CaretLeft size={22} weight="bold" />
            </button>
            <p className="itinerary-carousel__dots" aria-hidden>
              {stops.map((_, i) => (
                <span
                  key={i}
                  className={`itinerary-carousel__dot${i === activeIndex ? ' is-active' : ''}`}
                />
              ))}
            </p>
            <button
              type="button"
              className="itinerary-carousel__mobile-btn"
              aria-label="Next stop"
              onClick={goNext}
            >
              <CaretRight size={22} weight="bold" />
            </button>
          </div>
        )}
      </div>

      <div className="itinerary-featured">
        <AnimatePresence mode="wait">
          <motion.div
            key={`${active.phase}-${active.venue}-${activeIndex}`}
            className="itinerary-featured__copy"
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
            transition={{ duration: reduceMotion ? 0 : 0.28, ease: [0.16, 1, 0.3, 1] }}
            aria-live="polite"
          >
            <p className="itinerary-featured__kicker">{active.phase}</p>
            <h3
              className="itinerary-featured__title"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              {active.venue}
            </h3>
            <div className="itinerary-featured__meta">
              {active.category && <span>{active.category}</span>}
              {active.address && <span>{active.address}</span>}
              {affinity && <span>{affinity}</span>}
            </div>
            <p className="itinerary-featured__narrative">{active.vibe_narrative}</p>
          </motion.div>
        </AnimatePresence>

        <div className="itinerary-featured__actions">
          <button
            type="button"
            onClick={onReset}
            className="cursor-pointer rounded-full border border-[var(--ink)]/25 px-5 py-1.5 text-sm text-[var(--ink)]/70 transition-colors duration-200 hover:border-[var(--ink)] hover:text-[var(--ink)]"
          >
            Tweak vibe & regenerate
          </button>
        </div>
      </div>
    </div>
  );
}
