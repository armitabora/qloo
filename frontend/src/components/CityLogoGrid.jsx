import { useEffect, useState } from 'react';
import { fetchCities } from '../api';
import CityIcon from './cityIcons';

/**
 * Cities logo grid — layout mirrored from On the Grid (#cities):
 * navy field, white hairline grid, name + country, centered line-art mark,
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
      <div className="bg-[#07111f] px-6 py-16 text-center text-sm text-white/50">
        Loading cities…
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="border-t border-white/15 bg-[#07111f] px-6 py-10 text-center text-sm text-red-200">
        Could not load cities.
      </div>
    );
  }

  return (
    <section
      id="cities"
      aria-label="Cities"
      className="border-t border-white/20 bg-[#07111f] text-white"
    >
      <div className="border-b border-white/20 px-5 py-5 md:px-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/45">
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
              className={`group relative flex aspect-[4/5] cursor-pointer flex-col items-center overflow-hidden border-r border-b border-white/30 px-3 py-5 text-center transition-colors duration-200 ${
                selected
                  ? 'bg-white text-[#07111f]'
                  : 'bg-[#07111f] text-white hover:bg-white hover:text-[#07111f]'
              }`}
            >
              <div className="relative z-10 w-full px-1">
                <h3
                  className="text-[clamp(1.2rem,2.4vw,1.75rem)] font-bold leading-[1.05] tracking-[-0.02em]"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {city.label}
                </h3>
                <p className="mt-1.5 text-[11px] leading-snug opacity-70">
                  {city.country}
                </p>
              </div>

              <div className="relative z-10 flex flex-1 items-center justify-center py-3">
                <CityIcon
                  id={city.id}
                  className={`h-28 w-28 max-h-[46%] max-w-[72%] transition-transform duration-200 md:h-32 md:w-32 ${
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
