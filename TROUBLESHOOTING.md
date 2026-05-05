# Troubleshooting Guide

## Common Issues and Solutions

### ❌ Error 429: Rate Limit Exceeded (Garmin Authentication)

**Error message:**
```
HTTPSConnectionPool(host='connectapi.garmin.com', port=443): Max retries exceeded
(Caused by ResponseError('too many 429 error responses'))
```

**Cause:**
Garmin Connect has rate limiting to prevent automated logins. This error occurs when:
- First time running the sync (no saved tokens)
- Multiple rapid authentication attempts
- Garmin's anti-bot protection is triggered

**Solutions:**

1. **Wait 10-15 minutes** before retrying
   - Garmin's rate limit resets after a cool-down period
   - Do not trigger the workflow multiple times in quick succession

2. **Let the automatic retry work**
   - The script now includes automatic retry with exponential backoff (5s, 10s, 20s)
   - It will attempt 3 times with increasing delays

3. **After first successful authentication:**
   - Tokens are saved in `db/.garth/` directory
   - These tokens are committed to the repository
   - Future runs will use saved tokens (no login needed)
   - **No more rate limit errors after initial setup!**

4. **Manual workflow trigger:**
   - Go to Actions tab
   - Select the workflow
   - Click "Run workflow"
   - Wait for completion
   - Check if tokens were created in `db/.garth/`

### ✅ Verification Steps

After workflow runs successfully:

1. Check if `db/.garth/` contains:
   - `oauth1_token.json`
   - `oauth2_token.json`

2. If tokens exist:
   - Future runs will be automatic
   - No more authentication needed
   - Rate limit errors should not occur

### 🔒 Security Notes

**Token files grant access to your Garmin account:**
- Keep your repository **private**
- Do not share token files
- Tokens have long expiration (weeks/months)
- If compromised, change your Garmin password

### 📋 Best Practices

1. **First setup:**
   - Manually trigger the workflow once
   - Wait for successful completion
   - Verify tokens are saved

2. **Scheduled runs:**
   - Let cron schedule handle automatic syncs
   - Don't manually trigger too frequently

3. **If tokens expire:**
   - Delete old token files
   - Run workflow once to regenerate
   - Wait for rate limit cool-down if needed

### 🐛 Still Having Issues?

1. **Check GitHub Secrets:**
   - `GARMIN_EMAIL` - correct?
   - `GARMIN_PASSWORD` - correct?
   - `GARMIN_AUTH_DOMAIN` - "COM" or "CN"

2. **Check workflow logs:**
   - Look for authentication messages
   - Verify token directory creation
   - Check for saved token files

3. **Database issues:**
   - Delete `db/garmin.db` and `db/coros.db`
   - Let workflow recreate them

### 🌐 Region-Specific Issues

**China region (CN):**
- Use `GARMIN_AUTH_DOMAIN: CN`
- Different domain: `garmin.cn`
- May have different rate limits

**International (COM):**
- Use `GARMIN_AUTH_DOMAIN: COM`
- Default domain: `garmin.com`

---

## Other Common Errors

### Missing credentials
**Error:** `No activities found`
**Solution:** Verify GitHub Secrets are set correctly

### Import errors
**Error:** `ModuleNotFoundError`
**Solution:** Dependencies not installed. Check `requirements.txt`

### Permission denied (Git push)
**Error:** `Permission denied`
**Solution:** Check workflow permissions in repository settings

---

For more help, check:
- [GitHub Issues](../../issues)
- [Original README](README.md)
- Token directory info: `db/.garth/README.md`
