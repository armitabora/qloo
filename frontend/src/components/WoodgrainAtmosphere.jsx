/**
 * Silk beige field + antique gold woodgrain overlay.
 * Layout observed on insheepsclothinghifi.com (absolute SVG grain, 1px stroke,
 * preserveAspectRatio xMidYMid slice). Paths here are generated, not copied.
 * Colors follow the VibeGuide palette tokens in index.css.
 */
function buildGrainPaths(count = 96) {
  const paths = [];
  for (let i = 0; i < count; i += 1) {
    const seed = i * 9973 + 41;
    let x = (i * 20.8 + (seed % 19)) % 2000;
    let y = -30;
    let d = `M${x.toFixed(1)},${y}`;
    while (y < 1060) {
      const dy = 64 + ((seed + Math.floor(y) * 3) % 88);
      const wobble = 11 + (i % 11) * 1.8;
      const nx =
        x +
        Math.sin((y + seed) * 0.011) * wobble +
        (((seed >> 2) % 9) - 4);
      const c1x = x + (nx - x) * 0.28;
      const c1y = y + dy * 0.38;
      const c2x = nx - (nx - x) * 0.12;
      const c2y = y + dy * 0.72;
      d += `C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${nx.toFixed(1)},${(y + dy).toFixed(1)}`;
      x = nx;
      y += dy;
    }
    paths.push(d);
  }
  return paths;
}

const GRAIN_PATHS = buildGrainPaths();

export default function WoodgrainAtmosphere({ className = '' }) {
  return (
    <div className={`woodgrain-atmosphere ${className}`.trim()} aria-hidden>
      <svg
        className="woodgrain-atmosphere__svg"
        viewBox="0 0 2000 1000"
        preserveAspectRatio="xMidYMid slice"
      >
        {GRAIN_PATHS.map((d, i) => (
          <path key={i} d={d} />
        ))}
      </svg>
    </div>
  );
}
