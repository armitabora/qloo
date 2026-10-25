import img1 from '../assets/feelings/crossfade-1.jpg';
import img2 from '../assets/feelings/crossfade-2.jpg';

/**
 * Feelings Engine–style ambient background.
 * REA: .crossfading-background with 4 spans (images 1/1/2/2),
 * animation fade 16s (opacity 0.2→1→0.2), plus ::before blur(50px) overlay.
 */
export default function CrossfadeAtmosphere({ className = '' }) {
  return (
    <div
      className={`crossfade-atmosphere pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden
    >
      <span className="crossfade-atmosphere__layer" style={{ backgroundImage: `url(${img1})` }} />
      <span className="crossfade-atmosphere__layer" style={{ backgroundImage: `url(${img1})` }} />
      <span className="crossfade-atmosphere__layer" style={{ backgroundImage: `url(${img2})` }} />
      <span className="crossfade-atmosphere__layer" style={{ backgroundImage: `url(${img2})` }} />
      <div className="crossfade-atmosphere__veil" />
      <div className="crossfade-atmosphere__grain" />
    </div>
  );
}
