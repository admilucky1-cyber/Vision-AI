# Railway deploy notes (Vision AI)

## Force Docker (recommended)

Your logs showed **Railway Express** (Nixpacks), which may skip the Dockerfile.
Without Docker you often get **no ffmpeg** → lower quality / progressive stream only.

In Railway dashboard:

1. Service → **Settings** → **Build**
2. Set **Builder** to **Dockerfile**
3. Dockerfile path: `Dockerfile`
4. Redeploy

`railway.toml` already has:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"
```

If the UI still uses Express, override Builder manually in Settings.

## Mobile downloads

- Server always sends `Content-Disposition: attachment` + `application/octet-stream`
- Mobile client uses `window.location.assign(url?dl=1)` (no blob, no memory)
- Desktop can still use anchor/blob for small files

## Test

1. Desktop Edge + FDM: already works
2. Phone: tap **Click to download** → browser download notification should appear
3. If iOS only plays video: Share → Save to Files
