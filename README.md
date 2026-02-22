# Video Downloader

A secure video downloader service with authentication and YouTube bot detection bypass.

## Features

- 🔒 Session-based authentication with bcrypt password hashing
- 🎥 Downloads videos from YouTube and other platforms
- 🔄 Auto-fallback to Invidious for YouTube bot detection
- 🍪 Optional cookie support for private/age-restricted videos
- 💾 Persistent session storage
- 🔐 Environment variable configuration

## Setup

### Render Secret File Setup

1. Create a file named `credentials.json` with your credentials:
   ```json
   {
     "username": "your_username",
     "password": "your_password"
   }
   ```

2. On Render.com:
   - Go to your service dashboard
   - Navigate to **"Secret Files"** section
   - Click **"Add Secret File"**
   - Set **Filename:** `/etc/secrets/credentials`
   - Paste the contents of your `credentials.json`
   - Click **"Save"**

3. Redeploy your service

The password will be automatically hashed with bcrypt on startup.

### Default Credentials

If no secret file is configured:
- **Username:** `thepythoncoder6` (case insensitive)
- **Password:** `Qwertyuiop!`

⚠️ **Change these for production using Render Secret Files!**

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
bash start.sh
```

Or manually:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Security Features

- ✅ Bcrypt password hashing (not plaintext)
- ✅ Secure httponly session cookies
- ✅ Render Secret Files for credential storage
- ✅ Persistent session storage across restarts
- ✅ 24-hour session expiry
- ✅ Server-side authentication validation

## API Endpoints

- `POST /api/login` - Login with username/password
- `POST /api/logout` - Logout and clear session
- `POST /api/download` - Download video (requires auth)
- `GET /api/check-auth` - Check authentication status
- `GET /api/file/{filename}` - Download file

## Usage

1. Navigate to the site
2. Login with credentials
3. Paste video URL
4. (Optional) Add cookies for YouTube if needed
5. Click Download
6. Download the file

## YouTube Bot Detection

If YouTube blocks the download:
1. The service automatically tries Invidious fallback
2. If that fails, you can provide YouTube cookies in Netscape format
3. See [yt-dlp cookie guide](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
