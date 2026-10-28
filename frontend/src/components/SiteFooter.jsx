const LINKS = [
  { href: '/about', label: 'About' },
  { href: '/terms', label: 'Terms' },
  { href: '/privacy', label: 'Privacy' },
];

export default function SiteFooter({ tone = 'dark' }) {
  const onPaper = tone === 'paper';
  const border = onPaper ? 'border-[var(--ink)]/12' : 'border-[var(--color-border)]';
  const muted = onPaper ? 'text-[var(--ink-muted)]' : 'text-[var(--color-fg)]/45';
  const link = onPaper
    ? 'text-[var(--ink-muted)] hover:text-[var(--ink)]'
    : 'text-[var(--color-fg)]/55 hover:text-[var(--color-fg)]';
  const mark = onPaper ? 'text-[var(--ink)]' : 'text-[var(--color-fg)]';

  return (
    <footer className={`border-t ${border} px-6 py-10 md:px-10`}>
      <div className="mx-auto flex max-w-2xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <a
          href="/"
          className={`text-sm font-semibold tracking-[-0.02em] ${mark}`}
          style={{ fontFamily: 'var(--font-display)' }}
        >
          VibeGuide
        </a>
        <nav aria-label="Legal" className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {LINKS.map(({ href, label }) => (
            <a
              key={href}
              href={href}
              className={`text-sm transition-colors duration-200 ${link}`}
            >
              {label}
            </a>
          ))}
        </nav>
      </div>
      <p className={`mx-auto mt-6 max-w-2xl text-xs ${muted}`}>
        Taste-intelligent travel · powered by Qloo
      </p>
    </footer>
  );
}
