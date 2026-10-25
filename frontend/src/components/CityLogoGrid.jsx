import { useEffect, useState } from 'react';
import { fetchCities } from '../api';
import CityIcon from './cityIcons';

/**
 * Cities logo grid — layout mirrored from On the Grid (#cities):
 * emerald field, silk-beige hairline grid, name + country, centered line-art mark,
 * hover invert. Evidence: onthegrid.city#cities REA capture.
 */
export default function CityLogoGrid({ value, onChange }) {
  const [cities, setCities] = useState([]);
  const [loadError, setLoadError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchCities();
        if (cancelled) return;
        const list = [...(data.cities || [])].sort((a, b) =>
          a.label.localeCompare(b.label)
        );
        setCities(list);
        setLoadError(false);
      } catch {
        if (!cancelled) setLoadError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="bg-[var(--color-bg)] px-6 py-16 text-center text-sm text-[var(--color-fg)]/50">
        Loading cities…
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="border-t border-[var(--color-fg)]/15 bg-[var(--color-bg)] px-6 py-10 text-center text-sm text-[var(--color-danger-fg)]">
        Could not load cities.
      </div>
    );
  }

  return (
    <section
      id="cities"
      aria-label="Cities"
      className="border-t border-[var(--color-fg)]/20 bg-[var(--color-bg)] text-[var(--color-fg)]"
    >
      <div className="border-b border-[var(--color-fg)]/20 px-5 py-5 md:px-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-fg)]/45">
          Cities
        </p>
        <h2
          className="mt-1 text-[clamp(1.5rem,3vw,2rem)] font-bold tracking-[-0.02em]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          Choose a city
        </h2>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        {cities.map((city) => {
          const selected = city.id === value;
          return (
            <button
              key={city.id}
              type="button"
              onClick={() => onChange(city.id)}
              aria-pressed={selected}
              className={`group relative flex aspect-square cursor-pointer flex-col items-center overflow-hidden border-r border-b border-[var(--color-fg)]/30 px-2.5 py-3 text-center transition-colors duration-200 ${
                selected
                  ? 'bg-[var(--silk-beige)] text-[var(--ink)]'
                  : 'bg-[var(--color-bg)] text-[var(--color-fg)] hover:bg-[var(--silk-beige)] hover:text-[var(--ink)]'
              }`}
            >
              <div className="relative z-10 w-full px-1">
                <h3
                  className="text-[clamp(1rem,2vw,1.45rem)] font-bold leading-[1.05] tracking-[-0.02em]"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {city.label}
                </h3>
                <p className="mt-0.5 text-[10px] leading-snug opacity-70">
                  {city.country}
                </p>
              </div>

              <div className="relative z-10 flex min-h-0 flex-1 items-center justify-center">
                <CityIcon
                  id={city.id}
                  className={`h-[7.5rem] w-[7.5rem] max-h-[58%] max-w-[70%] transition-transform duration-200 ${
                    selected ? 'scale-105' : 'group-hover:scale-105'
                  }`}
                />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
