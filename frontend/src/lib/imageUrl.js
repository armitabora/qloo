const SIZE_KEYS = new Set(['maxwidth', 'maxheight', 'w', 'h', 'width', 'height']);

/**
 * Qloo/Google place photos often encode a thumbnail size in the URL.
 * Bump those params so carousel sleeves are not upscaled from 200–400px.
 */
export function upgradeImageUrl(url) {
  if (!url || typeof url !== 'string') return url;
  try {
    const parsed = new URL(url);
    let changed = false;
    for (const key of [...parsed.searchParams.keys()]) {
      if (!SIZE_KEYS.has(key.toLowerCase())) continue;
      const n = Number(parsed.searchParams.get(key));
      if (!Number.isNaN(n) && n < 1200) {
        parsed.searchParams.set(key, '1600');
        changed = true;
      }
    }
    if (/googleusercontent\.com|ggpht\.com/i.test(parsed.hostname)) {
      const eq = parsed.pathname.lastIndexOf('=');
      if (eq !== -1) {
        parsed.pathname = `${parsed.pathname.slice(0, eq)}=s1600`;
        changed = true;
      }
    }
    parsed.pathname = parsed.pathname.replace(
      /\/(\d{2,4})x(\d{2,4})\//,
      (match, w, h) => {
        if (Number(w) < 800 || Number(h) < 800) {
          changed = true;
          return '/1600x1600/';
        }
        return match;
      }
    );
    return changed ? parsed.toString() : url;
  } catch {
    return url.replace(/=[swh]\d+[a-z0-9=-]*$/i, '=s1600');
  }
}
