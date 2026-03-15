# API Authentication

Talk To Data v3 supports optional API key authentication to protect your instance from unauthorized access.

## Why Enable Authentication?

Without authentication, anyone who can reach your API can:
- Upload files → fill your disk
- Generate queries → drain your LLM credits
- Execute queries → DOS your database

**Recommendation:** Enable API auth for any public-facing deployment.

## Setup

### 1. Generate API Keys

Generate secure random keys:

```bash
openssl rand -hex 32
# Output: a1b2c3d4e5f6... (use this as an API key)
```

### 2. Configure Environment

Edit `backend/.env`:

```bash
REQUIRE_API_KEY=true
API_KEYS=key1_generated_above,key2_another_key,key3_third_key
```

**Multiple keys:** Comma-separated list allows you to:
- Issue different keys to different users
- Rotate keys without downtime
- Revoke individual keys

### 3. Restart Server

```bash
cd backend
uvicorn app.main:app --reload
```

## Usage

### API Requests

Include your API key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/api/v1/queries/generate \
  -H "X-API-Key: your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many users?"}'
```

### Frontend Configuration

Update your frontend to include the API key in all requests:

```typescript
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

fetch('http://localhost:8000/api/v1/queries/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
  body: JSON.stringify({ question: 'How many users?' }),
});
```

**Security Note:** In production, use server-side API calls to avoid exposing keys in browser.

## Excluded Paths

The following paths do NOT require an API key (always public):

- `/health` - Health check endpoint
- `/docs` - API documentation (Swagger UI)
- `/openapi.json` - OpenAPI schema
- `/redoc` - ReDoc documentation

## Error Responses

### Missing API Key (401)

```json
{
  "error": "Missing API key",
  "detail": "Include X-API-Key header with a valid API key"
}
```

### Invalid API Key (403)

```json
{
  "error": "Invalid API key",
  "detail": "The provided API key is not authorized"
}
```

## Key Rotation

To rotate keys without downtime:

1. Add new key to `API_KEYS`: `old_key,new_key`
2. Restart server
3. Update clients to use `new_key`
4. Once all clients migrated, remove `old_key`
5. Restart server again

## Disabling Authentication

To disable auth (e.g., for local development):

```bash
REQUIRE_API_KEY=false
```

or remove the `REQUIRE_API_KEY` line entirely (defaults to `false`).

## Best Practices

1. **Never commit API keys to git** - Use `.env` (already in `.gitignore`)
2. **Use long, random keys** - At least 32 characters (use `openssl rand -hex 32`)
3. **Rotate keys periodically** - Every 90 days or after any suspected breach
4. **Use HTTPS in production** - API keys sent over HTTP can be intercepted
5. **One key per client** - Makes revocation easier
6. **Monitor usage** - Track which keys are being used (TODO: add logging)

## Future Enhancements

- [ ] Rate limiting per API key
- [ ] Key expiration timestamps
- [ ] Usage metrics per key
- [ ] Admin API to manage keys dynamically
- [ ] OAuth2/JWT support
