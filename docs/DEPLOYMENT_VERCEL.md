# Step 15: Vercel Deployment — Next.js Frontend

**Project:** AI Study Assistant · **Date:** 22 November 2026
**Status:** Prepared and verified — production build passes, the API URL is
proven to bake into the bundle at build time, and the production server was
smoke-tested with all security headers present.

> What this step does NOT do: deploy anything. Vercel needs your account and
> your repo, so the deploy itself is a few clicks in the Vercel dashboard —
> Section 4 is the exact checklist. Deploy the backend to Railway first
> (Step 14, `DEPLOYMENT_RAILWAY.md`) — you need its URL for the frontend's
> only environment variable.

---

## 1. What changed and why

Vercel needs almost no configuration for a Next.js app — it auto-detects the
framework, installs, and builds. The real production work was elsewhere:

| Gap | Fix |
|---|---|
| `next.config.mjs` was empty (`{}`) — no strict mode, framework version leaked in headers, no security headers | Production `next.config.mjs` (§2) |
| No `vercel.json` | Minimal one, declaring the framework (§2) |
| No Node version declared — Vercel would pick whatever its current default is | `engines: { "node": ">=18.18" }` in `package.json` |
| No production env documentation — the only example was localhost | New `.env.production.example` (§3) |
| `.gitignore` didn't cover `.env` / `.env.production` — a real env file could be committed by accident | Both added |
| If `NEXT_PUBLIC_API_URL` is forgotten in Vercel, the app silently calls `localhost:8000` from every visitor's browser and every request fails with an opaque network error | `src/lib/api.ts` now logs a plain-English console error when a deployed page is talking to localhost (§3) |

## 2. Files

### `next.config.mjs` (production configuration)

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Don't advertise the framework version in response headers.
  poweredByHeader: false,

  // Security headers, applied to every route. These live here (rather than
  // vercel.json) so they travel with the app whatever host serves it.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
```

What each header does, in one line:

- **X-Content-Type-Options: nosniff** — browsers won't guess a file's type,
  so a hostile upload can't be executed as a script.
- **X-Frame-Options: DENY** — the app can't be embedded in another site's
  frame (clickjacking protection). Nothing in the app needs framing.
- **Referrer-Policy** — other sites learn only the origin, not the full page
  URL, when a user clicks out.
- **Permissions-Policy** — the browser features the app never uses (camera,
  microphone, geolocation) are switched off.
- **Strict-Transport-Security** — browsers remember to use HTTPS for two
  years. Safe: Vercel serves HTTPS only.

No `output: "standalone"` — that's for Docker/self-hosting. Vercel uses its
own output; setting standalone would only complicate the build.

### `vercel.json` (new)

```json
{
  "$schema": "https://vercel.com/schema/vercel.json",
  "framework": "nextjs"
}
```

Deliberately small: Vercel auto-detects Next.js, so the build/install/start
commands, output directory, and regions all take their correct defaults.
The Root Directory (`frontend`) is a **project setting in the dashboard**,
not something this file can set — see §4 step 2.

### `package.json`

```json
"engines": {
  "node": ">=18.18"
}
```

Next 14.2 requires Node ≥ 18.17. No upper bound, so a future Vercel Node
default won't break the deploy. (Verified locally on Node 24.)

### `.gitignore`

Added `.env` and `.env.production`. The `.example` files are still committed
— they're documentation, not secrets.

## 3. Environment configuration

The frontend has exactly **one** environment variable:

| Variable | Value | Where |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<your-api>.up.railway.app/api/v1` | Vercel → Settings → Environment Variables |

`.env.production.example` documents it with the Railway URL placeholder.
`.env.local.example` now points at it for production.

**The one gotcha that bites everyone:** `NEXT_PUBLIC_` variables are baked
into the JavaScript bundle **at build time**. Changing the value in the
Vercel dashboard does nothing until you redeploy (Deployments → ⋯ →
Redeploy). There is no way to change the API URL on a live deployment
without a rebuild — that's how Next.js works, not a bug.

**The silent-failure trap:** `src/lib/api.ts` falls back to
`http://localhost:8000/api/v1` when the variable is unset, which is correct
for local dev — but on a deployed site it means every API call goes to the
*visitor's own computer* and fails with a generic network error. The new
guard logs this to the console when a non-localhost page is using the
localhost API:

```ts
if (
  typeof window !== "undefined" &&
  API_URL.includes("localhost") &&
  !window.location.hostname.includes("localhost") &&
  window.location.hostname !== "127.0.0.1"
) {
  console.error(
    "AI Study Assistant: NEXT_PUBLIC_API_URL is not set — the app is calling " +
      "localhost:8000, which does not exist for your visitors. Set it in " +
      "Vercel (Settings → Environment Variables) and redeploy."
  );
}
```

## 4. Deploy checklist (Vercel dashboard)

1. **Deploy the backend first** (Step 14) and generate its public domain on
   Railway. You need `https://<your-api>.up.railway.app/api/v1`.
2. **Add New Project → Import** the same GitHub repo. Set the **Root
   Directory to `frontend`** (the repo also contains `backend/`). Framework
   Preset should auto-detect as Next.js — leave Build/Install commands at
   their defaults.
3. **Environment Variables:** add `NEXT_PUBLIC_API_URL` =
   `https://<your-api>.up.railway.app/api/v1` for Production (and Preview, so
   preview deployments work too).
4. **Deploy.** Watch the build log: `npm run build` must pass (type-check +
   lint + 13 static pages).
5. **Update the backend's CORS:** on Railway, set
   `CORS_ORIGINS=["https://<your-app>.vercel.app"]` and redeploy the API.
   Without this, the browser blocks every API call. (If you use Vercel
   preview deployments, add their URLs too, or preview logins will fail
   with CORS errors.)
6. **Smoke test the live site:** open the Vercel URL, register an account,
   log in, upload a PDF, and check the dashboard loads. If anything fails,
   open DevTools → Console: the `api.ts` guard (§3) will tell you if the
   API URL is the problem, and the Network tab will show CORS errors
   plainly.

## 5. Verification

- **Build with a production URL:** `NEXT_PUBLIC_API_URL=https://api.example.com/api/v1
  npm run build` passed, and the test URL was found baked into the built
  chunks (`login`, `register`, `layout`). The only `localhost:8000` string
  left in those chunks is the console.error message text — the fallback URL
  itself was compiled away.
- **Default build:** `npm run build` with no env var passes (type-check +
  lint + 13 static pages).
- **Production smoke test:** `next start` served `/`, `/login`, `/register`,
  `/dashboard` all 200, with all five security headers present and
  `x-powered-by` absent.
- **Metadata already correct:** the layout sets title "AI Study Assistant"
  with a real description — nothing of create-next-app's placeholder text
  remains.

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Build fails: `Cannot find module` / wrong files | Root Directory not set to `frontend` | Project → Settings → General → Root Directory → `frontend` |
| Login/register fail with network errors; console shows the `NEXT_PUBLIC_API_URL` error | Env var missing or set after the last deploy | Set it in Settings → Environment Variables, then **Redeploy** |
| API calls fail with CORS errors | Backend `CORS_ORIGINS` still localhost-only | Add the Vercel URL on Railway and redeploy the API |
| Changed the API URL but the site still calls the old one | Env vars bake in at build time | Redeploy — changing the variable alone does nothing |
| Preview deployments can't log in | Preview URLs aren't in the backend's CORS list | Add the preview URL to `CORS_ORIGINS`, or test auth only on the production URL |
| `npm run build` fails locally with an engine error | Node older than 18.18 | Upgrade Node (the project was verified on Node 24) |
