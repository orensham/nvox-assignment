# Nvox Journey API - Postman Collection Guide

## Quick Start

### 1. Start the Services

```bash
# From repository root - starts postgres, redis, and API
docker compose -f apps/nvox-api/docker-compose.yaml --profile api up -d

# Wait for services to be healthy
docker compose -f apps/nvox-api/docker-compose.yaml ps
```

### 2. Import the Collection
1. Open Postman
2. Click **Import**
3. Select `apps/nvox-api/Nvox_Journey_API.postman_collection.json`
4. Collection will appear in your sidebar

### 3. Run the Complete Flow
**Option A: Run Individual Requests**
- Execute requests 1-8 in order
- Watch the console for automatic variable updates (user_id, access_token)

**Option B: Run All at Once**
- Right-click collection → "Run collection"
- Click "Run Nvox Journey API"
- View execution results

## Request Overview

### Main Flow (Requests 1-8)

| # | Request | Description | What to Check |
|---|---------|-------------|---------------|
| 1 | Health Check | Verify API is running | Should return `{"alive": true}` |
| 2 | Signup | Create user + initialize journey | `journey.current_stage` = "REFERRAL" |
| 3 | Login | Get JWT token | Token auto-saved to variable |
| 4 | Get Current Journey | View REFERRAL stage | See available questions |
| 5a | Submit Boolean | Answer doesn't trigger transition | `transition_occurred` = false |
| 5b | High Karnofsky (80) | Triggers REFERRAL → WORKUP | `current_stage` = "WORKUP" |
| 5c | Low Karnofsky (30) | Triggers REFERRAL → EXIT | `current_stage` = "EXIT" |
| 6 | Get Updated Journey | See new stage | Questions for new stage |
| 7 | Update Answer | Test versioning | Old answer marked `is_current=false` |
| 8 | Delete User | Anonymize data | Can no longer login |

### Alternative Flow
Shows a complete journey from REFERRAL → WORKUP with a different user

## Debugging with Database

Connect to PostgreSQL:
```bash
docker exec -it nvox-postgres psql -U transplant_user -d transplant_journey
```

## Debugging with Redis

Connect to Redis CLI:
```bash
docker exec -it nvox-redis redis-cli
```

### List All Keys
```redis
KEYS *
```

## Variables (Auto-managed)

The collection automatically manages these variables:

- `base_url`: http://localhost:8000 (can change for different environments)
- `user_email`: Default test email (can modify)
- `user_password`: Default test password (can modify)
- `access_token`: Auto-updated on login
- `user_id`: Auto-updated on signup

## Tips for Local Debugging

1. **Watch Console Logs**: Check Postman console for variable updates
2. **Use Collection Runner**: Good for regression testing
3. **Modify Variables**: Test different emails/passwords
4. **Check Responses**: Look for `transition_occurred`, `current_stage`, `questions`

## Cleanup

Remove all test data:
```bash
# Restart services (clears data)
docker compose -f apps/nvox-api/docker-compose.yaml down -v
docker compose -f apps/nvox-api/docker-compose.yaml up -d
```

Or manually truncate tables:
```sql
TRUNCATE users, user_journey_state, user_answers, stage_transitions, user_journey_path CASCADE;
```
