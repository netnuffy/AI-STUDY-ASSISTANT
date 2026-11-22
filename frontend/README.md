# AI Study Assistant — Frontend

Next.js 14 (App Router, TypeScript) + Tailwind CSS + shadcn/ui. Talks to the
FastAPI backend in `../backend`.

## Quick start

```bash
# 1. Backend (in another terminal) — see ../backend/README.md
cd ../backend
uvicorn main:app --reload   # http://localhost:8000

# 2. Frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm install
npm run dev                        # http://localhost:3000
```

The backend's default CORS config already allows `http://localhost:3000`.

## Pages

| Route | Page |
|---|---|
| `/` | Landing page (public) |
| `/login` | Log in |
| `/register` | Create an account (auto-logs in afterwards) |
| `/dashboard` | Stats, recent summaries, quiz scores, documents, activity, log a session |
| `/upload` | Upload PDFs, view/delete documents, AI summary viewer |
| `/chat` | Chat with one document or all of them (RAG answers + page sources) |
| `/flashcards` | Generate and study flashcards (flip, mark known/unknown) |
| `/quiz` | Generate and take quizzes (MCQ, true/false, short answer) |
| `/planner` | Create study plans, track daily tasks, weekly goals, revision |

## How auth works

- Login posts OAuth2 form data (`username` = email) to `/auth/login` and
  stores the access token (15 min) + refresh token (7 days) in localStorage.
- `lib/api.ts` attaches the access token to every request. On a 401 it
  refreshes once and retries; if refresh fails it clears the tokens and
  sends the user to `/login`.
- `lib/auth.tsx` provides `useAuth()` (user, login, register, logout).
  `components/protected.tsx` guards every app page.

## Structure

```
src/
├── app/                  # Routes (App Router)
│   ├── page.tsx          # Landing
│   ├── login/ register/ dashboard/ upload/ chat/ flashcards/ quiz/ planner/
│   └── layout.tsx        # AuthProvider, navbar, toaster
├── components/
│   ├── ui/               # shadcn/ui primitives (button, card, dialog, ...)
│   ├── navbar.tsx
│   ├── protected.tsx     # Auth guard for app pages
│   └── document-picker.tsx
└── lib/
    ├── api.ts            # fetch wrapper + token refresh + login
    ├── auth.tsx          # AuthProvider / useAuth
    ├── types.ts          # Types mirroring the backend schemas
    └── utils.ts          # cn()
```

## Deployment (Vercel)

Import the repo into Vercel with the **Root Directory set to `frontend`**,
then set `NEXT_PUBLIC_API_URL` to the deployed Railway backend
(`https://<your-api>.up.railway.app/api/v1`) in Settings → Environment
Variables. `NEXT_PUBLIC_` values bake into the bundle at build time, so
changing the variable requires a redeploy. After the first deploy, add the
Vercel URL to the backend's `CORS_ORIGINS` on Railway or the browser will
block every API call. Production config lives in `next.config.mjs`
(strict mode, no `x-powered-by`, security headers) and `vercel.json`.
Full checklist: `~/workspace/your_files/DEPLOYMENT_VERCEL.md`.

## Notes

- `components.json` is the shadcn config — add more components with
  `npx shadcn@latest add <component>`.
- Production build: `npm run build && npm start`.
- The frontend never talks to Gemini or ChromaDB directly — everything goes
  through the backend API.
