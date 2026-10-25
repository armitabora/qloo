import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { feature } from 'topojson-client';
import worldAtlas from '../assets/countries-110m.json';
import { fetchCities } from '../api';

const WIDTH = 1000;
const HEIGHT = 500;
const MIN_ZOOM = 1;
const MAX_ZOOM = 7;
const ZOOM_LERP = 0.14;
const PAN_LERP = 0.18;

const COUNTRY_TO_REGION = {
  840: 'us',
  826: 'europe',
  250: 'europe',
  276: 'europe',
  528: 'europe',
  724: 'europe',
  380: 'europe',
  620: 'europe',
  372: 'europe',
  392: 'asia',
  410: 'asia',
  764: 'asia',
  158: 'asia',
  356: 'india',
  36: 'oceania',
  554: 'oceania',
};

const REGION_COLORS = {
  us: '#d4a373',
  europe: '#c49262',
  asia: '#3d5c48',
  india: '#b8845a',
  oceania: '#e8d4bc',
};

const REGION_ACCENT = {
  us: '#e0b88a',
  europe: '#d4a373',
  asia: '#5a7a64',
  india: '#c99a6e',
  oceania: '#f1e3d3',
};

const CABLE_COLORS = ['#d4a373', '#c49262', '#e0b88a', '#b8845a', '#e8d4bc'];

const BASE_LAND = '#2a4a38';
const MUTED_LAND = '#152820';
const LAND_STROKE = '#3d5c48';
const MARKER_RING = '#f1e3d3';
const MARKER_CORE = '#152820';
const HOVER_LAND = '#f1e3d3';
const FOCUS_LAND = '#e8d4bc';

function project(lat, lng) {
  const x = ((lng + 180) / 360) * WIDTH;
  const y = ((90 - lat) / 180) * HEIGHT;
  return { x, y };
}

function ringLngSpan(ring) {
  let minLng = Infinity;
  let maxLng = -Infinity;
  for (const [lng] of ring) {
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
  }
  return maxLng - minLng;
}

function pathFromProjected(points) {
  if (points.length < 3) return '';
  return (
    points
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`)
      .join(' ') + 'Z'
  );
}

/**
 * Convert a ring to SVG path data. Rings that cross the antimeridian are split
 * into continuous projected pieces and closed along the dateline (x=0 or x=WIDTH)
 * so we never fill a full-width horizontal band or blank out a map section.
 */
function ringToPath(ring) {
  if (!ring?.length) return '';

  const open =
    ring[0][0] === ring[ring.length - 1][0] &&
    ring[0][1] === ring[ring.length - 1][1]
      ? ring.slice(0, -1)
      : ring;

  if (open.length < 3) return '';

  const pts = open.map(([lng, lat]) => project(lat, lng));

  // Split on dateline jumps AND on Natural Earth's long parallel "stitches"
  // (near-horizontal edges that span most of the map → the dark bars)
  const isSeam = (a, b) => {
    const dx = Math.abs(b.x - a.x);
    const dy = Math.abs(b.y - a.y);
    return dx > WIDTH * 0.5 || (dx > WIDTH * 0.3 && dy < 4);
  };

  const needsSplit =
    ringLngSpan(open) > 180 || pts.some((p, i) => i > 0 && isSeam(pts[i - 1], p));

  if (!needsSplit) {
    return pathFromProjected(pts);
  }

  const pieces = [];
  let piece = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    if (isSeam(pts[i - 1], pts[i])) {
      pieces.push(piece);
      piece = [pts[i]];
    } else {
      piece.push(pts[i]);
    }
  }
  pieces.push(piece);

  // If last→first is not a seam, merge last piece into first
  if (pieces.length > 1 && !isSeam(pieces[pieces.length - 1].at(-1), pieces[0][0])) {
    const last = pieces.pop();
    pieces[0] = last.concat(pieces[0]);
  }

  return pieces
    .map((seg) => {
      if (seg.length < 3) return '';
      const first = seg[0];
      const last = seg[seg.length - 1];
      const bothLeft = first.x < WIDTH / 2 && last.x < WIDTH / 2;
      const bothRight = first.x >= WIDTH / 2 && last.x >= WIDTH / 2;
      if (!bothLeft && !bothRight) return '';
      const edge = bothLeft ? 0 : WIDTH;
      return pathFromProjected(
        seg.concat([
          { x: edge, y: last.y },
          { x: edge, y: first.y },
          first,
        ])
      );
    })
    .filter(Boolean)
    .join(' ');
}

function polygonToPath(coordinates) {
  return coordinates.map(ringToPath).filter(Boolean).join(' ');
}

function geometryToPath(geometry) {
  if (!geometry) return '';
  if (geometry.type === 'Polygon') {
    return polygonToPath(geometry.coordinates);
  }
  if (geometry.type === 'MultiPolygon') {
    return geometry.coordinates.map(polygonToPath).filter(Boolean).join(' ');
  }
  return '';
}

function visitProjectedRing(ring, visit) {
  if (!ring?.length) return;
  if (ringLngSpan(ring) > 180) {
    // Approximate bounds from non-jumping segments only
    const open =
      ring[0][0] === ring[ring.length - 1][0] &&
      ring[0][1] === ring[ring.length - 1][1]
        ? ring.slice(0, -1)
        : ring;
    let prev = null;
    for (const [lng, lat] of open) {
      const { x, y } = project(lat, lng);
      if (prev && Math.abs(x - prev.x) > WIDTH * 0.5) {
        prev = { x, y };
        continue;
      }
      visit(x, y);
      prev = { x, y };
    }
    return;
  }
  for (const [lng, lat] of ring) {
    const { x, y } = project(lat, lng);
    visit(x, y);
  }
}

/** Soft arc between two map points — cable-map style, not a geodesic. */
function cablePath(a, b, bend = 0.22) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const cx = mx - dy * bend;
  const cy = my + dx * bend;
  return `M${a.x.toFixed(1)},${a.y.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}`;
}

function boundsFromGeometry(geometry) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const visit = (x, y) => {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  };
  if (!geometry) return null;
  if (geometry.type === 'Polygon') {
    geometry.coordinates.forEach((ring) => visitProjectedRing(ring, visit));
  } else if (geometry.type === 'MultiPolygon') {
    for (const poly of geometry.coordinates) {
      poly.forEach((ring) => visitProjectedRing(ring, visit));
    }
  } else {
    return null;
  }
  if (!Number.isFinite(minX)) return null;
  return { minX, minY, maxX, maxY };
}

/** Camera that frames a projected bbox (transformOrigin 50% / 45%). */
function viewForBBox(bbox, { pad = 1.35, minScale = 1.8, maxScale = MAX_ZOOM } = {}) {
  const { minX, minY, maxX, maxY } = bbox;
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const bw = Math.max(maxX - minX, 18);
  const bh = Math.max(maxY - minY, 18);
  const scale = clamp(
    Math.min(WIDTH / (bw * pad), HEIGHT / (bh * pad)),
    minScale,
    maxScale
  );
  const ox = WIDTH * 0.5;
  const oy = HEIGHT * 0.45;
  // translate% after scale-around-origin → t = -scale * (c - origin)
  const tx = (-scale * (cx - ox) / WIDTH) * 100;
  const ty = (-scale * (cy - oy) / HEIGHT) * 100;
  return { scale, tx, ty };
}

/** Polar landmasses removed from the chart */
const HIDDEN_COUNTRY_IDS = new Set([
  10, // Antarctica
  260, // Fr. S. Antarctic Lands
  304, // Greenland (Arctic)
]);

const FEATURE_COUNTRY_ALIASES = {
  'United States of America': ['United States', 'USA', 'US'],
  'United Kingdom': ['United Kingdom', 'UK', 'England'],
  'South Korea': ['South Korea', 'Korea'],
  'Hong Kong': ['Hong Kong'],
  Singapore: ['Singapore'],
};

function featureMatchesCityCountry(featName, cityCountry) {
  const aliases = FEATURE_COUNTRY_ALIASES[featName] || [featName];
  const needle = cityCountry.toLowerCase();
  return aliases.some((a) => a.toLowerCase() === needle);
}

const WORLD_FEATURES = feature(worldAtlas, worldAtlas.objects.countries)
  .features.filter((f) => !HIDDEN_COUNTRY_IDS.has(Number(f.id)))
  .map((f) => ({
    id: Number(f.id),
    name: f.properties?.name || '',
    region: COUNTRY_TO_REGION[Number(f.id)] || null,
    path: geometryToPath(f.geometry),
    bounds: boundsFromGeometry(f.geometry),
  }));

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n));
}

export default function CityMapPicker({ value, onChange, hero = false }) {
  const [cities, setCities] = useState([]);
  const [loadError, setLoadError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mapRegion, setMapRegion] = useState('world');
  const [hoveredCountry, setHoveredCountry] = useState(null);
  const [focusCountry, setFocusCountry] = useState(null);
  const [hoveredCity, setHoveredCity] = useState(null);
  const [renderTick, setRenderTick] = useState(0);

  const mapShellRef = useRef(null);
  const unbindMapRef = useRef(null);
  const targetRef = useRef({ scale: 1.05, tx: 0, ty: 0 });
  const currentRef = useRef({ scale: 1.05, tx: 0, ty: 0 });
  const dragRef = useRef({ active: false, x: 0, y: 0, tx: 0, ty: 0 });
  const rafRef = useRef(0);

  const reduceMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchCities();
        if (cancelled) return;
        setCities(data.cities || []);
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

  useEffect(() => {
    let alive = true;
    const tick = () => {
      if (!alive) return;
      const t = targetRef.current;
      const c = currentRef.current;
      const lerp = reduceMotion ? 1 : ZOOM_LERP;
      const panLerp = reduceMotion ? 1 : PAN_LERP;
      const ns = c.scale + (t.scale - c.scale) * lerp;
      const ntx = c.tx + (t.tx - c.tx) * panLerp;
      const nty = c.ty + (t.ty - c.ty) * panLerp;
      if (
        Math.abs(ns - c.scale) > 0.0004 ||
        Math.abs(ntx - c.tx) > 0.01 ||
        Math.abs(nty - c.ty) > 0.01
      ) {
        c.scale = ns;
        c.tx = ntx;
        c.ty = nty;
        setRenderTick((n) => n + 1);
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      alive = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [reduceMotion]);

  const setTargetView = useCallback((partial) => {
    targetRef.current = {
      ...targetRef.current,
      ...partial,
      scale: clamp(partial.scale ?? targetRef.current.scale, MIN_ZOOM, MAX_ZOOM),
    };
  }, []);

  const zoomBy = useCallback(
    (factor) => {
      const next = clamp(targetRef.current.scale * factor, MIN_ZOOM, MAX_ZOOM);
      setTargetView({
        scale: next,
        tx: targetRef.current.tx,
        ty: targetRef.current.ty,
      });
      if (next <= 1.12) {
        setMapRegion('world');
        setFocusCountry(null);
      }
    },
    [setTargetView]
  );

  const citiesByFeatureId = useMemo(() => {
    const map = new Map();
    for (const feat of WORLD_FEATURES) {
      const matches = cities.filter((c) =>
        featureMatchesCityCountry(feat.name, c.country)
      );
      if (matches.length) map.set(feat.id, matches);
    }
    return map;
  }, [cities]);

  const snapCountry = useCallback(
    (feat) => {
      const countryCities = citiesByFeatureId.get(feat.id);
      if (!feat || !countryCities?.length) return;

      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;
      for (const city of countryCities) {
        const { x, y } = project(city.lat, city.lng);
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
      const pad = countryCities.length === 1 ? 36 : 22;
      const view = viewForBBox(
        {
          minX: minX - pad,
          minY: minY - pad,
          maxX: maxX + pad,
          maxY: maxY + pad,
        },
        { pad: 1.25, minScale: 2.8, maxScale: MAX_ZOOM }
      );
      setFocusCountry(feat.id);
      if (feat.region) setMapRegion(feat.region);
      setTargetView(view);
    },
    [citiesByFeatureId, setTargetView]
  );

  const selected = useMemo(
    () => cities.find((c) => c.id === value) || null,
    [cities, value]
  );

  const selectCity = useCallback(
    (city) => {
      onChange(city.id);
      const { x, y } = project(city.lat, city.lng);
      const pad = 48;
      const view = viewForBBox(
        { minX: x - pad, minY: y - pad, maxX: x + pad, maxY: y + pad },
        { pad: 1.1, minScale: 3.4, maxScale: MAX_ZOOM }
      );
      setFocusCountry(null);
      setMapRegion(city.region);
      setTargetView(view);
    },
    [onChange, setTargetView]
  );

  const bindMapShell = useCallback(
    (node) => {
      unbindMapRef.current?.();
      unbindMapRef.current = null;
      mapShellRef.current = node;
      if (!node) return;

      const onWheel = (e) => {
        // Zoom only with Ctrl/Cmd + scroll; plain scroll leaves the page
        if (!e.ctrlKey && !e.metaKey) return;
        e.preventDefault();
        e.stopPropagation();
        const rect = node.getBoundingClientRect();
        const mx = (e.clientX - rect.left) / rect.width - 0.5;
        const my = (e.clientY - rect.top) / rect.height - 0.5;
        const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? rect.height : 1;
        const delta = -e.deltaY * unit * 0.0016;
        const prev = targetRef.current.scale;
        const next = clamp(prev * Math.exp(delta), MIN_ZOOM, MAX_ZOOM);
        const ratio = next / prev;
        setTargetView({
          scale: next,
          tx: targetRef.current.tx - mx * 36 * (ratio - 1) * next,
          ty: targetRef.current.ty - my * 24 * (ratio - 1) * next,
        });
        if (next <= 1.12) {
          setMapRegion('world');
          setFocusCountry(null);
        }
      };

      const onDown = (e) => {
        if (e.button !== 0) return;
        if (e.target.closest?.('[data-map-ui]')) return;
        dragRef.current = {
          active: true,
          x: e.clientX,
          y: e.clientY,
          tx: targetRef.current.tx,
          ty: targetRef.current.ty,
        };
        node.style.cursor = 'grabbing';
      };
      const onMove = (e) => {
        if (!dragRef.current.active) return;
        const dx = ((e.clientX - dragRef.current.x) / node.clientWidth) * 100;
        const dy = ((e.clientY - dragRef.current.y) / node.clientHeight) * 100;
        setTargetView({
          scale: targetRef.current.scale,
          tx: dragRef.current.tx + dx,
          ty: dragRef.current.ty + dy,
        });
      };
      const onUp = () => {
        dragRef.current.active = false;
        node.style.cursor = 'grab';
      };

      node.addEventListener('wheel', onWheel, { passive: false });
      node.addEventListener('pointerdown', onDown);
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
      unbindMapRef.current = () => {
        node.removeEventListener('wheel', onWheel);
        node.removeEventListener('pointerdown', onDown);
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
      };
    },
    [setTargetView]
  );

  useEffect(() => () => unbindMapRef.current?.(), []);

  const view = currentRef.current;
  void renderTick;

  const markers = useMemo(() => {
    if (mapRegion === 'world') return cities;
    return cities.filter((c) => c.region === mapRegion);
  }, [cities, mapRegion]);

  // Region-local cable rings (not a full mesh)
  const cables = useMemo(() => {
    const byRegion = {};
    for (const city of markers) {
      (byRegion[city.region] ||= []).push(city);
    }
    const links = [];
    let colorIdx = 0;
    for (const regionCities of Object.values(byRegion)) {
      if (regionCities.length < 2) continue;
      for (let i = 0; i < regionCities.length; i++) {
        const a = regionCities[i];
        const b = regionCities[(i + 1) % regionCities.length];
        if (i === regionCities.length - 1 && regionCities.length < 3) break;
        links.push({
          id: `${a.id}-${b.id}`,
          a: project(a.lat, a.lng),
          b: project(b.lat, b.lng),
          color: CABLE_COLORS[colorIdx % CABLE_COLORS.length],
          active:
            a.id === value ||
            b.id === value ||
            a.id === hoveredCity ||
            b.id === hoveredCity,
        });
        colorIdx += 1;
      }
    }
    return links;
  }, [markers, value, hoveredCity]);

  if (loading) {
    return (
      <div className="flex h-[70svh] items-center justify-center text-sm text-[var(--color-muted)]">
        Charting destinations…
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="m-6 rounded-2xl border border-[var(--color-danger)]/40 bg-[var(--color-danger-bg)] p-4 text-sm text-[var(--color-danger-fg)]">
        Could not load cities. Is the backend running on port 8000?
      </div>
    );
  }

  return (
    <div
      className={`relative w-full overflow-hidden ${
        hero ? 'h-[100svh] min-h-[640px]' : 'h-[520px] rounded-2xl border border-[var(--color-border)]'
      }`}
    >
      {/* Full-bleed map stage */}
      <div
        ref={bindMapShell}
        className="absolute inset-0 cursor-grab touch-none bg-[var(--velvet-deep)]"
        style={{ touchAction: 'pan-y' }}
      >
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-full w-full"
          preserveAspectRatio="xMidYMid slice"
          role="img"
          aria-label="Interactive world map. Ctrl+scroll or use buttons to zoom, drag to pan."
        >
          <defs>
            <radialGradient id="velvet" cx="48%" cy="40%" r="85%">
              <stop offset="0%" stopColor="var(--velvet-lit)" />
              <stop offset="100%" stopColor="var(--velvet-deep)" />
            </radialGradient>
          </defs>
          {/* Oversized so pan/zoom never reveals a hard velvet edge */}
          <rect
            x={-WIDTH}
            y={-HEIGHT}
            width={WIDTH * 3}
            height={HEIGHT * 3}
            fill="url(#velvet)"
          />

          <g
            style={{
              transform: `translate(${view.tx}%, ${view.ty}%) scale(${view.scale})`,
              transformOrigin: '50% 45%',
            }}
          >
            {WORLD_FEATURES.map((feat) => {
              if (!feat.path) return null;
              const hasDestinations = citiesByFeatureId.has(feat.id);
              const isFocused = focusCountry === feat.id;
              const isActiveRegion =
                !focusCountry &&
                mapRegion !== 'world' &&
                feat.region === mapRegion;
              const dim =
                (focusCountry && focusCountry !== feat.id) ||
                (!focusCountry &&
                  mapRegion !== 'world' &&
                  hasDestinations &&
                  feat.region !== mapRegion);
              let fill = hasDestinations
                ? REGION_COLORS[feat.region] || BASE_LAND
                : MUTED_LAND;
              if ((isActiveRegion || isFocused) && hasDestinations) {
                fill = REGION_ACCENT[feat.region] || FOCUS_LAND;
              }
              if (hasDestinations && hoveredCountry === feat.id) fill = HOVER_LAND;
              // No dark outline on muted land — long E–W coasts were reading as bars
              const stroke = !hasDestinations
                ? 'none'
                : isFocused || isActiveRegion
                  ? 'rgba(241,227,211,0.35)'
                  : LAND_STROKE;
              return (
                <path
                  key={feat.id}
                  d={feat.path}
                  fill={fill}
                  fillOpacity={
                    dim
                      ? 0.22
                      : isFocused || isActiveRegion
                        ? 0.98
                        : hasDestinations
                          ? 0.88
                          : 0.75
                  }
                  stroke={stroke}
                  strokeOpacity={hasDestinations ? 0.45 : 0}
                  strokeWidth={
                    (isFocused || isActiveRegion ? 0.85 : 0.4) /
                    Math.sqrt(view.scale)
                  }
                  className={hasDestinations ? 'cursor-pointer' : undefined}
                  style={{ pointerEvents: hasDestinations ? 'auto' : 'none' }}
                  onMouseEnter={() =>
                    hasDestinations && setHoveredCountry(feat.id)
                  }
                  onMouseLeave={() => setHoveredCountry(null)}
                  onClick={() => hasDestinations && snapCountry(feat)}
                  aria-hidden={!hasDestinations}
                  aria-label={
                    hasDestinations
                      ? `${feat.name}, ${feat.region || 'destination'} cities`
                      : undefined
                  }
                />
              );
            })}

            {/* Region-local cable arcs (no SVG filter — filters + CSS transform cause dark bands) */}
            <g fill="none">
              {cables.map((link) => (
                <path
                  key={link.id}
                  d={cablePath(
                    link.a,
                    link.b,
                    0.18 + (link.id.length % 5) * 0.03
                  )}
                  stroke={link.color}
                  strokeOpacity={link.active ? 0.85 : 0.32}
                  strokeWidth={
                    (link.active ? 1.6 : 0.95) / Math.sqrt(view.scale)
                  }
                  strokeLinecap="round"
                />
              ))}
            </g>

            {markers.map((city) => {
              const { x, y } = project(city.lat, city.lng);
              const isSelected = city.id === value;
              const isHover = city.id === hoveredCity;
              const r =
                (isSelected ? 5.5 : isHover ? 4.5 : 3.4) / Math.sqrt(view.scale);
              return (
                <g
                  key={city.id}
                  onMouseEnter={() => setHoveredCity(city.id)}
                  onMouseLeave={() => setHoveredCity(null)}
                >
                  {(isSelected || isHover) && (
                    <circle
                      cx={x}
                      cy={y}
                      r={r + 5 / Math.sqrt(view.scale)}
                      fill="none"
                      stroke={MARKER_RING}
                      strokeWidth={1.1 / Math.sqrt(view.scale)}
                      opacity={0.9}
                    />
                  )}
                  <circle
                    cx={x}
                    cy={y}
                    r={r + 1.6 / Math.sqrt(view.scale)}
                    fill={MARKER_CORE}
                    stroke={MARKER_RING}
                    strokeWidth={0.8 / Math.sqrt(view.scale)}
                    className="cursor-pointer"
                  />
                  <circle
                    cx={x}
                    cy={y}
                    r={r}
                    fill={isSelected ? MARKER_RING : REGION_COLORS[city.region] || FOCUS_LAND}
                    className="cursor-pointer"
                    role="button"
                    tabIndex={0}
                    aria-label={`${city.label}, ${city.country}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      selectCity(city);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        selectCity(city);
                      }
                    }}
                  />
                  {(isSelected || (isHover && view.scale > 1.4)) && (
                    <text
                      x={x}
                      y={y - r - 9 / Math.sqrt(view.scale)}
                      textAnchor="middle"
                      fill={MARKER_RING}
                      fontSize={Math.max(10, 13 / Math.sqrt(view.scale * 0.55))}
                      fontWeight="700"
                      style={{
                        pointerEvents: 'none',
                        fontFamily: 'var(--font-display)',
                      }}
                    >
                      {city.label}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {hero && (
        <div data-map-ui className="pointer-events-none absolute left-0 top-0 z-10 w-[min(24rem,88vw)]">
          <div className="map-lockup">
            <p className="mb-3 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-fg)]/45">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-[var(--color-fg)]/20 text-[10px] text-[var(--color-fg)]/70">
                1
              </span>
              Choose a city
            </p>
            <p className="max-w-[28ch] text-sm leading-relaxed text-[var(--color-muted)]">
              Drag to pan. Ctrl+scroll to zoom. Land on a city that fits your taste.
            </p>
          </div>
        </div>
      )}

      {/* Zoom controls */}
      <div
        data-map-ui
        className="absolute bottom-20 left-4 z-20 flex flex-col overflow-hidden rounded-lg border border-[var(--color-fg)]/15 bg-[var(--velvet-deep)]/85 backdrop-blur-md md:bottom-8 md:left-6"
      >
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => zoomBy(1.35)}
          className="cursor-pointer px-3 py-2 text-lg leading-none text-[var(--color-fg)]/85 transition-colors hover:bg-[var(--color-fg)]/10 hover:text-[var(--color-fg)]"
        >
          +
        </button>
        <div className="h-px bg-[var(--color-fg)]/10" />
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => zoomBy(1 / 1.35)}
          className="cursor-pointer px-3 py-2 text-lg leading-none text-[var(--color-fg)]/85 transition-colors hover:bg-[var(--color-fg)]/10 hover:text-[var(--color-fg)]"
        >
          −
        </button>
      </div>

      {/* Bottom selection strip */}
      {hero && selected && (
        <div
          data-map-ui
          className="absolute bottom-0 left-0 z-20 flex w-full items-center justify-between gap-4 border-t border-[var(--color-fg)]/10 bg-[var(--velvet-deep)]/88 px-5 py-3 backdrop-blur-md md:px-6"
        >
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--color-fg)]/40">
              Selected
            </p>
            <p className="truncate text-base font-semibold text-[var(--color-fg)] md:text-lg">
              {selected.label}
              <span className="font-normal text-[var(--color-fg)]/45"> · {selected.country}</span>
            </p>
          </div>
          <a
            href="#vibe"
            className="shrink-0 cursor-pointer rounded-full bg-[var(--silk-beige)] px-5 py-2.5 text-sm font-semibold text-[var(--ink)] transition-transform duration-200 hover:scale-[0.98] hover:bg-[color-mix(in_oklch,var(--silk-beige)_88%,var(--antique-gold))]"
          >
            Set vibe →
          </a>
        </div>
      )}
    </div>
  );
}
