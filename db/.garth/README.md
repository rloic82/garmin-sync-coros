# Garmin Authentication Tokens Directory

This directory stores OAuth tokens for Garmin Connect authentication.

## Important Notes

### First Run
On the first execution, this directory will be empty and the script will attempt to authenticate with Garmin using your credentials. **Garmin has rate limiting (HTTP 429 errors)** to prevent automated logins.

### Rate Limiting Issues
If you encounter a `429 Too Many Requests` error:
1. **Wait 5-10 minutes** before trying again
2. The script includes automatic retry with exponential backoff
3. Once authentication succeeds, tokens will be saved here for future use

### Token Files
After successful authentication, you'll see:
- `oauth1_token.json` - OAuth1 token for Garmin API
- `oauth2_token.json` - OAuth2 token for Garmin API

### Security
⚠️ **These tokens grant access to your Garmin account.** 
- Do NOT share these files publicly
- Keep them in a private repository
- They are automatically saved and reused to avoid repeated login attempts

### GitHub Actions
For GitHub Actions:
1. First successful run will save tokens
2. Commit and push the tokens back to the repository
3. Future runs will reuse these tokens (no login needed)
4. Tokens should remain valid for extended periods

## Troubleshooting

### Error: Rate limit exceeded (429)
**Solution:** Wait 10-15 minutes before retrying. Garmin blocks frequent authentication attempts.

### Error: Token files not found
**Solution:** Normal on first run. The script will authenticate and create them.

### Error: Authentication failed
**Solution:** Verify your Garmin credentials in GitHub Secrets are correct.
