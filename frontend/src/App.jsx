import { useEffect, useState } from 'react';
import { useReducedMotion } from 'motion/react';
import { ReactLenis, useLenis } from 'lenis/react';
import CityMapPicker from './components/CityMapPicker';
import IntroTitle from './components/IntroTitle';
import CityLogoGrid from './components/CityLogoGrid';
import CyclingPromptField from './components/CyclingPromptField';
import CrossfadeAtmosphere from './components/CrossfadeAtmosphere';
import ItineraryCarousel from './components/ItineraryCarousel';
import SiteFooter from './components/SiteFooter';
import {
  AboutPage,
  NotFoundPage,
  PrivacyPage,
  TermsPage,
} from './components/StaticPage';
import WoodgrainAtmosphere from './components/WoodgrainAtmosphere';
import VibeOutputDissolve from './components/VibeOutputDissolve';
import { generateItinerary } from './api';

const UNRECOGNIZED_ANCHORS =
  "Those entries don't match an artist, film, or mood, so there's no day to build. Try a real name, like Radiohead or Studio Ghibli.";

const KEYBOARD_ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
const SHORT_ROW_WORDS = new Set(['sad', 'dad', 'pop']);

function sameRowCluster(compact) {
  if (compact.length < 3 || !/^[a-z]+$/.test(compact)) return false;
  if (SHORT_ROW_WORDS.has(compact)) return false;
  if (compact.length === 4 && compact.slice(0, 2) === compact.slice(2)) return false;
  const cols = [];
  let row = null;
  for (const ch of compact) {
    let found = null;
    KEYBOARD_ROWS.forEach((keys, rowIndex) => {
      const col = keys.indexOf(ch);
      if (col >= 0) found = [col, rowIndex];
    });
    if (!found) return false;
    const [col, rowIndex] = found;
    if (row === null) row = rowIndex;
    else if (rowIndex !== row) return false;
    cols.push(col);
  }
  return Math.max(...cols) - Math.min(...cols) <= 2;
}

function looksLikeGibberish(text) {
  const compact = text.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]/g, '');
  if (compact.length < 2) return true;
  if (compact.length >= 4 && new Set(compact).size === 1) return true;
  for (let size = 1; size <= Math.floor(compact.length / 2); size += 1) {
    if (compact.length % size !== 0) continue;
    const reps = compact.length / size;
    if (compact.slice(0, size).repeat(reps) !== compact) continue;
    if ((size >= 3 && reps >= 2) || reps >= 3) return true;
  }
  if (
    compact.length >= 4 &&
    KEYBOARD_ROWS.some((row) => row.includes(compact) || [...row].reverse().join('').includes(compact))
  ) {
    return true;
  }
  return sameRowCluster(compact);
}

function SectionLabel({ step, children, tone = 'light' }) {
  const muted = tone === 'dark' ? 'text-[var(--ink-muted)]' : 'text-[var(--color-fg)]/40';
  const ring =
    tone === 'dark'
      ? 'border-[var(--ink)]/25 text-[var(--ink)]/70'
      : 'border-[var(--color-fg)]/20 text-[var(--color-fg)]/70';
  return (
    <p className={`mb-4 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.16em] ${muted}`}>
      <span className={`inline-flex h-6 w-6 items-center justify-center rounded-full border text-[10px] ${ring}`}>
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
  const [anchorError, setAnchorError] = useState('');
  const [apiError, setApiError] = useState(false);
  const lenis = useLenis();
  const reduceMotion = useReducedMotion();

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
    if (!lenis) return;
    lenis.resize();
    if (!itinerary || isLoading) return undefined;
    const timer = window.setTimeout(() => {
      lenis.resize();
      const target = document.getElementById('output');
      if (!target) return;
      lenis.scrollTo(target, {
        offset: 0,
        duration: reduceMotion ? 0.2 : 1.85,
        easing: (t) => 1 - (1 - t) ** 3,
      });
    }, reduceMotion ? 0 : 120);
    return () => window.clearTimeout(timer);
  }, [itinerary, isLoading, lenis, reduceMotion]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError(false);
    setAnchorError('');
    setApiError(false);
    setItinerary(null);

    const filled = [formData.music, formData.film, formData.vibe]
      .map((value) => value.trim())
      .filter(Boolean);

    if (filled.length === 0) {
      setValidationError(true);
      lenis?.scrollTo('#vibe');
      return;
    }
    if (filled.every(looksLikeGibberish)) {
      setAnchorError(UNRECOGNIZED_ANCHORS);
      lenis?.scrollTo('#vibe');
      return;
    }
    if (!formData.city) {
      setValidationError(true);
      lenis?.scrollTo('#city', { offset: -24 });
      return;
    }

    setIsLoading(true);

    try {
      const data = await generateItinerary(formData);
      setItinerary(data);
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching itinerary:', error);
      const detail = error.body?.detail;
      const unrecognized =
        error.status === 422 &&
        detail &&
        typeof detail === 'object' &&
        !Array.isArray(detail) &&
        detail.code === 'unrecognized_anchors';
      if (unrecognized) {
        setAnchorError(detail.message || UNRECOGNIZED_ANCHORS);
        setIsLoading(false);
        lenis?.scrollTo('#vibe');
        return;
      }
      setApiError(true);
      setIsLoading(false);
    }
  };

  const resetOutput = () => {
    setApiError(false);
    setIsLoading(false);
    if (!lenis) return;
    const target = document.getElementById('vibe-start') || document.getElementById('vibe');
    if (!target) return;
    lenis.resize();
    window.requestAnimationFrame(() => {
      lenis.scrollTo(target, {
        offset: 0,
        duration: reduceMotion ? 0.2 : 1.85,
        easing: (t) => 1 - (1 - t) ** 3,
        lock: true,
      });
    });
  };

  const hasOutput = Boolean(itinerary);

  return (
    <div className="bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* ── 1. Title, then the city map it dissolves into ─────────── */}
      <IntroTitle>
        <CityMapPicker
          hero
          value={formData.city}
          onChange={(city) => {
            setFormData({ ...formData, city });
            setValidationError(false);
          }}
        />
      </IntroTitle>

      {/* Cities logo grid — On the Grid #cities pattern */}
      <CityLogoGrid
        value={formData.city}
        onChange={(city) => {
          setFormData({ ...formData, city });
          setValidationError(false);
          lenis?.scrollTo('#vibe');
        }}
      />

      <form onSubmit={handleSubmit}>
        <VibeOutputDissolve
          active={hasOutput}
          atmosphere={<CrossfadeAtmosphere />}
          reveal={
            hasOutput ? (
              <section
                id={reduceMotion ? 'output' : undefined}
                className={`output-section isolate flex flex-col justify-center py-10 md:py-12 ${
                  reduceMotion
                    ? 'relative min-h-svh overflow-hidden'
                    : 'sticky top-0 z-0 h-svh overflow-hidden'
                }`}
                aria-labelledby="output-heading"
                aria-live="polite"
              >
                <WoodgrainAtmosphere />
                <div className="relative z-10">
                  <div className="mx-auto max-w-2xl px-6 md:px-10">
                    <SectionLabel step="3" tone="dark">
                      Your day
                    </SectionLabel>
                  </div>
                  <ItineraryCarousel itinerary={itinerary} onReset={resetOutput} />
                </div>
              </section>
            ) : null
          }
        >
          <SectionLabel step="2">Set your vibe</SectionLabel>
          <h2
            id="vibe-heading"
            className="text-[clamp(1.75rem,4vw,2.75rem)] font-bold tracking-[-0.03em] text-[var(--color-fg)]"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            Your cultural anchors
          </h2>
          <p className="mt-3 max-w-xl text-[var(--color-accent)]">
            Tell Qloo what you love. We cross music, film, and vibe into a day that feels like you
            in {formData.city || 'your city'}.
          </p>

          {validationError && (
            <div
              role="alert"
              className="mt-6 rounded-xl border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger-fg)]"
            >
              Choose a city on the map and enter at least one cultural anchor.
            </div>
          )}
          {anchorError && (
            <div
              role="alert"
              className="mt-6 rounded-xl border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger-fg)]"
            >
              {anchorError}
            </div>
          )}

          <div className="mt-10 space-y-4">
            <CyclingPromptField
              id="music"
              leadIn="Favorite music is…"
              examples={['Radiohead', 'Daft Punk', 'Bon Iver', 'Tame Impala']}
              value={formData.music}
              error={validationError}
              onChange={(e) => {
                setFormData({ ...formData, music: e.target.value });
                setValidationError(false);
                setAnchorError('');
              }}
            />
            <CyclingPromptField
              id="film"
              leadIn="Favorite film or director is…"
              examples={['Studio Ghibli', 'Wes Anderson', 'Blade Runner', 'Christopher Nolan']}
              value={formData.film}
              error={validationError}
              onChange={(e) => {
                setFormData({ ...formData, film: e.target.value });
                setValidationError(false);
                setAnchorError('');
              }}
            />
            <CyclingPromptField
              id="vibe-input"
              leadIn="Today I want to feel…"
              examples={[
                'cyberpunk neon',
                'cozy lo-fi',
                'golden hour calm',
                'brutalist and bold',
              ]}
              value={formData.vibe}
              error={validationError}
              onChange={(e) => {
                setFormData({ ...formData, vibe: e.target.value });
                setValidationError(false);
                setAnchorError('');
              }}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="mt-12 cursor-pointer rounded-full bg-[var(--silk-beige)] px-8 py-3.5 text-sm font-semibold text-[var(--ink)] transition-transform duration-200 hover:scale-[0.98] hover:bg-[color-mix(in_oklch,var(--silk-beige)_88%,var(--antique-gold))] active:scale-[0.96] disabled:cursor-wait disabled:opacity-60"
          >
            {isLoading ? 'Generating…' : 'Generate my day'}
          </button>
          {isLoading && (
            <p className="mt-4 text-sm tracking-wide text-[var(--color-fg)]/70">{loadingPhrases[loadingTextIndex]}</p>
          )}
          {apiError && !isLoading && (
            <div
              role="alert"
              className="mt-6 max-w-md rounded-xl border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger-fg)]"
            >
              The city might be quiet right now, or the API needs a moment. Adjust your anchors
              and try again.
            </div>
          )}
        </VibeOutputDissolve>
      </form>
      <SiteFooter />
    </div>
  );
}

function normalizePath(pathname) {
  const trimmed = pathname.replace(/\/+$/, '');
  return trimmed === '' ? '/' : trimmed;
}

export default function App() {
  const path = normalizePath(window.location.pathname);

  if (path === '/about') return <AboutPage />;
  if (path === '/terms') return <TermsPage />;
  if (path === '/privacy') return <PrivacyPage />;
  if (path !== '/') return <NotFoundPage />;

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
