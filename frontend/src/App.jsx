import { useEffect, useRef, useState } from 'react';
import { ReactLenis, useLenis } from 'lenis/react';
import CityMapPicker from './components/CityMapPicker';
import CityLogoGrid from './components/CityLogoGrid';
import { generateItinerary } from './api';

function ParallaxLayer({ speed = 0.15, className = '', children }) {
  const ref = useRef(null);

  useLenis(({ scroll }) => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.style.transform = 'none';
      return;
    }
    el.style.transform = `translate3d(0, ${scroll * speed * -0.08}px, 0)`;
  });

  return (
    <div ref={ref} className={className} data-scroll-speed={speed}>
      {children}
    </div>
  );
}

function SectionLabel({ step, children }) {
  return (
    <p className="mb-4 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-white/40">
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-white/20 text-[10px] text-white/70">
        {step}
      </span>
      {children}
    </p>
  );
}

function AppShell() {
  const [formData, setFormData] = useState({
    city: 'Tokyo',
    music: '',
    film: '',
    vibe: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [loadingTextIndex, setLoadingTextIndex] = useState(0);
  const [itinerary, setItinerary] = useState(null);
  const [validationError, setValidationError] = useState(false);
  const [apiError, setApiError] = useState(false);
  const lenis = useLenis();

  const loadingPhrases = [
    'Analyzing your taste…',
    'Mapping the city…',
    'Writing your itinerary…',
    'Finalizing details…',
  ];

  useEffect(() => {
    let interval;
    if (isLoading) {
      interval = setInterval(() => {
        setLoadingTextIndex((prev) => (prev + 1) % loadingPhrases.length);
      }, 2000);
    } else {
      setLoadingTextIndex(0);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  useEffect(() => {
    if ((itinerary || isLoading || apiError) && lenis) {
      lenis.scrollTo('#output', { offset: -24 });
    }
  }, [itinerary, isLoading, apiError, lenis]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError(false);
    setApiError(false);
    setItinerary(null);

    if (!formData.music && !formData.film && !formData.vibe) {
      setValidationError(true);
      lenis?.scrollTo('#vibe', { offset: -24 });
      return;
    }
    if (!formData.city) {
      setValidationError(true);
      lenis?.scrollTo('#city', { offset: -24 });
      return;
    }

    setIsLoading(true);
    lenis?.scrollTo('#output', { offset: -24 });

    try {
      const data = await generateItinerary(formData);
      setTimeout(() => {
        setItinerary(data);
        setIsLoading(false);
      }, 4500);
    } catch (error) {
      console.error('Error fetching itinerary:', error);
      setTimeout(() => {
        setApiError(true);
        setIsLoading(false);
      }, 1500);
    }
  };

  const resetOutput = () => {
    setItinerary(null);
    setApiError(false);
    setIsLoading(false);
    lenis?.scrollTo('#vibe', { offset: -24 });
  };

  const hasOutput = isLoading || apiError || itinerary;

  return (
    <div className="bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* ── 1. City chooser ───────────────────────────────────────── */}
      <section id="city" className="relative" aria-label="Choose a city">
        <CityMapPicker
          hero
          value={formData.city}
          onChange={(city) => {
            setFormData({ ...formData, city });
            setValidationError(false);
          }}
        />
      </section>

      {/* Cities logo grid — On the Grid #cities pattern */}
      <CityLogoGrid
        value={formData.city}
        onChange={(city) => {
          setFormData({ ...formData, city });
          setValidationError(false);
          lenis?.scrollTo('#vibe', { offset: -24 });
        }}
      />

      <form onSubmit={handleSubmit}>
        {/* ── 2. Vibe input ─────────────────────────────────────────── */}
        <section
          id="vibe"
          className="relative border-t border-[var(--color-border)] px-6 py-20 md:px-10 md:py-28"
          aria-labelledby="vibe-heading"
        >
          <ParallaxLayer
            speed={0.35}
            className="pointer-events-none absolute -left-10 top-10 h-64 w-64 rounded-full bg-[var(--color-accent-soft)] blur-3xl"
          />
          <ParallaxLayer
            speed={0.55}
            className="pointer-events-none absolute -right-16 bottom-0 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl"
          />

          <div className="relative mx-auto max-w-2xl">
            <SectionLabel step="2">Set your vibe</SectionLabel>
            <h2
              id="vibe-heading"
              className="text-[clamp(1.75rem,4vw,2.75rem)] font-bold tracking-[-0.03em] text-white"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              Your cultural anchors
            </h2>
            <p className="mt-3 max-w-xl text-[var(--color-muted)]">
              Tell Qloo what you love. We cross music, film, and vibe into a day that feels like you
              in {formData.city || 'your city'}.
            </p>

            {validationError && (
              <div
                role="alert"
                className="mt-6 rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-sm text-red-200"
              >
                Choose a city on the map and enter at least one cultural anchor.
              </div>
            )}

            <div className="mt-10 space-y-8">
              <div>
                <label
                  htmlFor="music"
                  className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.14em] text-white/40"
                >
                  Favorite music
                </label>
                <input
                  id="music"
                  type="text"
                  placeholder="Radiohead, Daft Punk…"
                  className={`w-full border-b bg-transparent pb-3 text-lg transition-colors duration-200 placeholder:text-white/25 focus:outline-none ${
                    validationError
                      ? 'border-red-500'
                      : 'border-white/15 focus:border-white'
                  }`}
                  value={formData.music}
                  onChange={(e) => {
                    setFormData({ ...formData, music: e.target.value });
                    setValidationError(false);
                  }}
                />
              </div>
              <div>
                <label
                  htmlFor="film"
                  className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.14em] text-white/40"
                >
                  Favorite film or director
                </label>
                <input
                  id="film"
                  type="text"
                  placeholder="Studio Ghibli, Wes Anderson…"
                  className={`w-full border-b bg-transparent pb-3 text-lg transition-colors duration-200 placeholder:text-white/25 focus:outline-none ${
                    validationError
                      ? 'border-red-500'
                      : 'border-white/15 focus:border-white'
                  }`}
                  value={formData.film}
                  onChange={(e) => {
                    setFormData({ ...formData, film: e.target.value });
                    setValidationError(false);
                  }}
                />
              </div>
              <div>
                <label
                  htmlFor="vibe-input"
                  className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.14em] text-white/40"
                >
                  Desired vibe
                </label>
                <input
                  id="vibe-input"
                  type="text"
                  placeholder="Cyberpunk neon, cozy lo-fi…"
                  className={`w-full border-b bg-transparent pb-3 text-lg transition-colors duration-200 placeholder:text-white/25 focus:outline-none ${
                    validationError
                      ? 'border-red-500'
                      : 'border-white/15 focus:border-white'
                  }`}
                  value={formData.vibe}
                  onChange={(e) => {
                    setFormData({ ...formData, vibe: e.target.value });
                    setValidationError(false);
                  }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-12 cursor-pointer rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-black transition-transform duration-200 hover:scale-[0.98] hover:bg-slate-100 active:scale-[0.96] disabled:cursor-wait disabled:opacity-60"
            >
              {isLoading ? 'Generating…' : 'Generate my day'}
            </button>
          </div>
        </section>
      </form>

      {/* ── 3. Output ─────────────────────────────────────────────── */}
      <section
        id="output"
        className="relative min-h-[70svh] border-t border-[var(--color-border)] px-6 py-20 md:px-10 md:py-28"
        aria-labelledby="output-heading"
        aria-live="polite"
      >
        <div className="mx-auto max-w-2xl">
          <SectionLabel step="3">Your day</SectionLabel>

          {!hasOutput && (
            <div className="mt-2">
              <h2
                id="output-heading"
                className="text-[clamp(1.75rem,4vw,2.75rem)] font-bold tracking-[-0.03em] text-white"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                Your itinerary appears here
              </h2>
              <p className="mt-3 max-w-lg text-[var(--color-muted)]">
                Pick a city, set your anchors, then generate. This section fills with a day shaped
                around your taste.
              </p>
              <div className="mt-12 space-y-6 opacity-40" aria-hidden>
                {['Morning', 'Afternoon', 'Evening'].map((phase) => (
                  <div key={phase} className="border-l border-white/20 pl-6">
                    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-white/50">
                      {phase}
                    </p>
                    <div className="mt-2 h-3 w-2/3 rounded bg-white/10" />
                    <div className="mt-3 h-16 w-full rounded-r-xl bg-white/5" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {isLoading && (
            <div className="flex min-h-[40svh] flex-col items-center justify-center gap-6">
              <div
                className="h-9 w-9 animate-spin rounded-full border-2 border-white/20 border-t-white"
                aria-hidden
              />
              <p className="text-lg tracking-wide text-white/80">
                {loadingPhrases[loadingTextIndex]}
              </p>
            </div>
          )}

          {apiError && !isLoading && (
            <div className="flex min-h-[40svh] flex-col items-start justify-center gap-6">
              <h2
                id="output-heading"
                className="text-[clamp(1.75rem,4vw,2.75rem)] font-bold tracking-[-0.03em] text-white"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                Vibe check failed
              </h2>
              <p className="max-w-md text-[var(--color-muted)]">
                The city might be quiet right now, or the API needs a moment. Adjust your anchors and
                try again.
              </p>
              <button
                type="button"
                onClick={resetOutput}
                className="cursor-pointer rounded-full border border-white/25 px-6 py-2 text-sm text-white/90 transition-colors duration-200 hover:border-white hover:text-white"
              >
                Back to vibe
              </button>
            </div>
          )}

          {itinerary && !isLoading && (
            <div>
              <h2
                id="output-heading"
                className="text-[clamp(1.75rem,4vw,2.75rem)] font-bold tracking-[-0.03em] text-white"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                Your vibe in {itinerary.city}
              </h2>
              {itinerary.is_fallback && (
                <p className="mt-4 text-sm text-amber-300/90">
                  Showing a fallback day. Live Qloo recommendations were unavailable for this run.
                </p>
              )}
              <div className="relative ml-3 mt-14 space-y-12 border-l border-white/15 pb-8">
                {itinerary.stops.map((stop, idx) => (
                  <article key={idx} className="relative pl-8">
                    <div className="absolute top-1.5 -left-[5px] h-2.5 w-2.5 rounded-full bg-white" />
                    <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.14em] text-white/40">
                      {stop.phase}
                    </p>
                    <h3 className="mb-3 text-xl font-semibold text-white">{stop.venue}</h3>
                    <blockquote className="rounded-r-xl bg-[#121a2b] p-4 text-sm leading-relaxed text-white/75 italic">
                      {stop.vibe_narrative}
                    </blockquote>
                  </article>
                ))}
              </div>
              <div className="mt-14">
                <button
                  type="button"
                  onClick={resetOutput}
                  className="cursor-pointer rounded-full border border-white/25 px-6 py-2 text-sm text-white/70 transition-colors duration-200 hover:border-white hover:text-white"
                >
                  Tweak vibe & regenerate
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default function App() {
  return (
    <ReactLenis
      root
      options={{
        autoRaf: true,
        anchors: true,
        allowNestedScroll: true,
        respectReducedMotion: true,
        lerp: 0.09,
      }}
    >
      <AppShell />
    </ReactLenis>
  );
}
