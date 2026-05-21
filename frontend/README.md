# SmartCut AI — frontend

Next.js 16 (App Router) + React 19 + Tailwind 4 + shadcn/ui + Supabase Auth +
TanStack Query.

This is a **template scaffold** — the legacy React/Vite frontend lives under
[../old/frontend/](../old/frontend/) and should be ported into this app
incrementally.

## Stack

| Concern        | Choice                                         |
|----------------|------------------------------------------------|
| Framework      | Next.js 16 (App Router, Turbopack)             |
| Language       | TypeScript 5                                   |
| Styling        | Tailwind CSS 4                                 |
| UI primitives  | shadcn/ui (in `src/components/ui/`)            |
| Theme          | `next-themes`, dark default, key `aiat-theme`  |
| Server state   | `@tanstack/react-query` v5                     |
| Auth           | `@supabase/ssr` + `@supabase/supabase-js`      |
| Backend client | `src/lib/api.ts` (bearer token injected)       |

## Requirements

- **Node ≥ 20.9** (Next 16 requirement — the scaffolding warns on Node 18).
- A Supabase project bootstrapped with the SQL in [../db/](../db/).
- The FastAPI backend running at `NEXT_PUBLIC_API_URL`.

## Getting started

```bash
cp .env.example .env.local
# fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, NEXT_PUBLIC_API_URL
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Layout

```
src/
├── app/
│   ├── layout.tsx          # Providers: theme, query, toaster
│   ├── page.tsx            # Landing — redirects to /sessions when signed in
│   ├── sign-in/page.tsx    # TODO: Supabase auth form
│   ├── sign-up/page.tsx    # TODO: signup (passes full_name to options.data)
│   └── sessions/page.tsx   # TODO: port from old/frontend/src/pages/Sessions.tsx
├── components/
│   ├── theme-provider.tsx
│   ├── query-provider.tsx
│   └── ui/                 # shadcn primitives
├── lib/
│   ├── api.ts              # Typed fetch with bearer-token injection
│   ├── supabase/
│   │   ├── client.ts       # Browser client
│   │   ├── server.ts       # Server Components / Server Actions client
│   │   └── middleware.ts   # Session refresh + route gate
│   └── utils.ts            # cn() helper
└── middleware.ts           # Wires updateSession on every request
```

## Porting from `old/frontend/`

See [../old/frontend/design/09-missing-features.md](../old/frontend/design/09-missing-features.md)
for the auth / projects / members features the new UI needs to add. Existing
flows to port (sessions list, timeline editor, branding tab, intro library,
export modal) all live under [../old/frontend/src/](../old/frontend/src/).

The shadcn components already installed are `button`, `card`, `dialog`,
`dropdown-menu`, `input`, `label`, `select`, `badge`, `avatar`, `skeleton`,
`sonner`. Add more with `npx shadcn@latest add <component>`.
