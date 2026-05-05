⚠️ **First Run - Important Information**

If you see **Error 429 (Rate Limit Exceeded)** during first authentication:

1. **This is normal** - Garmin blocks automated logins
2. **Wait 10-15 minutes** before retrying
3. **After first success**, tokens are saved and reused
4. **Future runs** will not require authentication

📖 **See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed help**

---

## Quick Start

1. Set GitHub Secrets (see main README.md)
2. Run workflow manually first time
3. Wait for successful completion
4. Tokens saved in `db/.garth/`
5. Automatic sync works from then on!

✅ **Success indicators:**
- Files created: `db/.garth/oauth1_token.json` and `oauth2_token.json`
- Log message: "✓ Garmin authentication successful!"
- Subsequent runs use saved tokens (no login)
