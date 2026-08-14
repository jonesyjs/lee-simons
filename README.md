# leesimons.com

Personal portfolio site, built with Next.js and deployed to Cloudflare Workers via OpenNext.

## Features

- ⚡ Next.js 16 App Router with React 19
- 🎨 Tailwind CSS v4 styling
- 🔤 Google Fonts — Geist, League Spartan, Libre Baskerville
- 🖼️ Custom image loader (edge-friendly, no Next image optimization server)
- ☁️ Deployed to Cloudflare Workers with OpenNext
- 🤖 Agentic developer workflow layer (`adw/`) for spec → plan → build → review

## Prerequisites

- Node.js 18+
- npm
- A Cloudflare account (for deploy/preview)

## Setup

```bash
npm install
```

## Quick Start

```bash
npm run dev
```

The dev server runs at http://localhost:3000.

## Development

```bash
npm run dev        # Start the Next.js dev server
npm run build      # Production build
npm run lint       # Run ESLint
```

## Deployment

Deploys to Cloudflare Workers (`leesimons-com`) via OpenNext.

```bash
npm run preview    # Build with OpenNext and run locally via wrangler dev
npm run deploy     # Build with OpenNext and deploy with wrangler
```

## Project Structure

```
.
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # Root layout, fonts, metadata
│   │   ├── page.tsx            # Home page
│   │   └── globals.css         # Global styles (Tailwind)
│   ├── components/
│   │   └── design-specimen-card.tsx
│   └── image-loader.ts         # Custom image loader
│
├── adw/                        # Agentic Developer Workflow (see adw/README.md)
├── spec/                       # Generated specs (plan → build handoff)
├── ai_docs/                    # Docs + solution architecture
│
├── next.config.ts             # Next.js config (custom image loader)
├── open-next.config.ts        # OpenNext / Cloudflare config
└── wrangler.jsonc             # Cloudflare Workers config
```

## Tech Stack

- **Framework:** Next.js 16 (App Router), React 19
- **Styling:** Tailwind CSS v4
- **Language:** TypeScript
- **Hosting:** Cloudflare Workers via `@opennextjs/cloudflare`

## Related

- **`adw/`** — deterministic Python pipeline that wraps agent calls into gated stages. See [`adw/README.md`](adw/README.md).
- **`ai_docs/`** — documentation and solution architecture referenced during builds.
- **`spec/`** — generated specs, the plan→build artifact.
