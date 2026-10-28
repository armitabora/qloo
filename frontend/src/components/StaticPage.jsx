import SiteFooter from './SiteFooter';

function PageChrome({ title, children }) {
  return (
    <div className="flex min-h-svh flex-col bg-[var(--color-bg)] text-[var(--color-fg)]">
      <header className="border-b border-[var(--color-border)] px-6 py-5 md:px-10">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-4">
          <a
            href="/"
            className="text-lg font-bold tracking-[-0.03em] text-[var(--color-fg)]"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            VibeGuide
          </a>
          <a
            href="/"
            className="text-sm text-[var(--color-fg)]/55 transition-colors hover:text-[var(--color-fg)]"
          >
            Back home
          </a>
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12 md:px-10 md:py-16">
        <h1
          className="text-[clamp(2rem,5vw,2.75rem)] font-bold tracking-[-0.03em] text-[var(--color-fg)]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {title}
        </h1>
        <div className="mt-8 space-y-6 text-base leading-relaxed text-[var(--color-muted)]">
          {children}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="space-y-3">
      <h2
        className="text-lg font-semibold tracking-[-0.02em] text-[var(--color-fg)]"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

const DEMO_NOTE =
  'This page is demo copy for the VibeGuide project. It is not a substitute for legal counsel.';

export function AboutPage() {
  return (
    <PageChrome title="About">
      <p>
        VibeGuide is a taste-intelligent travel concierge. You pick a city and a few cultural
        anchors — music, film, mood — and it builds a one-day itinerary that feels like you
        instead of another generic top-ten list.
      </p>
      <Section title="How a day is built">
        <p>
          Your choices go from this app to a FastAPI backend, which asks Qloo for cross-domain
          taste insights and places in that city. Short “why it fits your vibe” lines come from
          Google Gemini when a key is configured; otherwise the backend falls back to a simple
          template.
        </p>
      </Section>
      <Section title="What to expect">
        <p>
          Stops are suggestions drawn from taste data and city search — not bookings, verified
          opening hours, or a complete map of every venue. Details can be incomplete. Treat the
          day as a starting point you refine in the real world.
        </p>
      </Section>
      <Section title="Why it exists">
        <p>
          VibeGuide was built for the Qloo Agentic Hackathon as a demo of cultural AI applied to
          travel. It is a product experiment, not a booking service or travel agency.
        </p>
      </Section>
    </PageChrome>
  );
}

export function TermsPage() {
  return (
    <PageChrome title="Terms of Service">
      <p className="text-sm text-[var(--color-fg)]/40">Last updated 28 October 2026</p>
      <Section title="The service">
        <p>
          VibeGuide is a hackathon demo that suggests a one-day city itinerary from cultural
          anchors you provide. Access is offered as-is, without warranties of any kind — including
          fitness for a particular purpose, accuracy, or uninterrupted availability.
        </p>
      </Section>
      <Section title="Suggestions, not bookings">
        <p>
          Itineraries are ideas, not reservations or verified listings. Do not rely on them for
          safety, opening hours, pricing, accessibility, or availability. Confirm venues yourself
          before you go.
        </p>
      </Section>
      <Section title="Accounts and your input">
        <p>
          There are no user accounts. What you type stays yours; we do not claim ownership of your
          anchors or feedback. Do not submit content that is unlawful or that you have no right to
          share.
        </p>
      </Section>
      <Section title="Third-party services">
        <p>
          Recommendations and narratives may depend on Qloo and Google. Those providers have their
          own terms. VibeGuide does not control their uptime or output.
        </p>
      </Section>
      <Section title="Limitation">
        <p>
          To the fullest extent allowed by law, the people behind this demo are not liable for
          losses arising from use of the site or from acting on an itinerary. If you disagree with
          these terms, do not use the demo.
        </p>
      </Section>
      <p className="border-t border-[var(--color-border)] pt-6 text-sm text-[var(--color-fg)]/40">
        {DEMO_NOTE}
      </p>
    </PageChrome>
  );
}

export function PrivacyPage() {
  return (
    <PageChrome title="Privacy Policy">
      <p className="text-sm text-[var(--color-fg)]/40">Last updated 28 October 2026</p>
      <Section title="No accounts or tracking">
        <p>
          VibeGuide does not offer accounts, set cookies for analytics, or run third-party
          tracking pixels. Closing the tab clears the itinerary in the page; nothing is kept in a
          user profile.
        </p>
      </Section>
      <Section title="What a generation sends">
        <p>
          When you generate a day, the app posts your city plus music, film, and vibe fields to
          our backend. Those fields are forwarded to Qloo for taste and place lookup. Taste context
          may also be sent to Google Gemini when a narrative key is configured, so the short
          explanations can be written.
        </p>
      </Section>
      <Section title="What we store">
        <p>
          We do not write itineraries or anchors to a database. The server may log request failures
          and, when you refine a plan, the city plus your instruction text. Logs exist for
          operations and debugging, not for marketing.
        </p>
      </Section>
      <Section title="We do not sell data">
        <p>
          Cultural anchors and itinerary text are not sold. They are used only to produce the
          response you asked for and to keep the demo running.
        </p>
      </Section>
      <p className="border-t border-[var(--color-border)] pt-6 text-sm text-[var(--color-fg)]/40">
        {DEMO_NOTE}
      </p>
    </PageChrome>
  );
}

export function NotFoundPage() {
  return (
    <PageChrome title="Page not found">
      <p>That path is not part of VibeGuide. Head back home to plan a day.</p>
      <p>
        <a
          href="/"
          className="font-semibold text-[var(--color-accent)] underline-offset-4 hover:underline"
        >
          Return home
        </a>
      </p>
    </PageChrome>
  );
}
