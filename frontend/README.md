# Mypedia frontend

Next.js student learning interface and parent/teacher dashboard for Mypedia.

## Setup

Copy the example environment file:

```powershell
Copy-Item .env.local.example .env.local
```

Set the public backend URL in `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Install and run:

```powershell
npm install
npm run dev
```

Open `http://localhost:3000` and sign in with the demo credentials:

```text
username: user123
password: devpost12345
```

## Scripts

```powershell
npm run dev
npm run build
npm run start
```

## Deployment

Deploy this app to Vercel or another Next.js-compatible host. Set `NEXT_PUBLIC_API_BASE_URL` to the public Render backend URL, then add the frontend domain to the backend's `CORS_ORIGINS` setting.

The Gemini key and database URL belong only in the backend deployment.
