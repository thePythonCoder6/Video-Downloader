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

### Environment Variables

For production, set these environment variables:

```bash
# Required for custom credentials
LOGIN_USERNAME=your_username
LOGIN_PASSWORD_HASH=your_bcrypt_hash

# Or use plain password (will be hashed on startup)
LOGIN_USERNAME=your_username
LOGIN_PASSWORD=your_password
```

### Generate Password Hash

To generate a bcrypt hash for your password, run:

```python
import bcrypt
password = "YourSecurePassword123!"
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
print(hash)
```

Or the app will generate one on first startup and print it to the console.

### Render.com Setup

1. Go to your Render service dashboard
2. Navigate to "Environment" section
3. Add environment variables:
   - `LOGIN_USERNAME` = `your_username`
   - `LOGIN_PASSWORD_HASH` = `$2b$12$...` (your bcrypt hash)

### Default Credentials

If no environment variables are set:
- **Username:** `thepythoncoder6` (case insensitive)
- **Password:** `Qwertyuiop!`

⚠️ **Change these for production!**

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
- ✅ Environment variable configuration
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
