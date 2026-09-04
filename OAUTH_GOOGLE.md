# Google OAuth setup (Vision AI)

## 1. Google Cloud Console

1. https://console.cloud.google.com/apis/credentials
2. Create **OAuth 2.0 Client ID** → Web application
3. **Authorized JavaScript origins**
   - `http://localhost:5050`
   - `https://YOUR-RAILWAY-DOMAIN.up.railway.app`
4. **Authorized redirect URIs** (exact match required)
   - `http://localhost:5050/auth/google/callback`
   - `https://YOUR-RAILWAY-DOMAIN.up.railway.app/auth/google/callback`

## 2. Environment variables

```env
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-....
GOOGLE_REDIRECT_URI=https://YOUR-RAILWAY-DOMAIN.up.railway.app/auth/google/callback
APP_BASE_URL=https://YOUR-RAILWAY-DOMAIN.up.railway.app
SESSION_SECRET=<long random string>
SECRET_KEY=<long random string>
DEBUG=false
```

## 3. Verify

- `GET /auth/login/debug` → `oauth_available: true`
- Login page → **Continue with Google**
- After consent → app home with session

## Common failures

| Symptom | Cause |
|---------|--------|
| `redirect_uri_mismatch` | URI in Google Console ≠ `GOOGLE_REDIRECT_URI` |
| `session_expired_retry` | Cookie blocked / wrong SESSION_SECRET / http vs https |
| `oauth_not_configured` | Missing CLIENT_ID or SECRET on Railway |
| Button does nothing | Authlib not installed (`pip install authlib`) |
