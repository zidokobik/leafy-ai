# Safety API

All endpoints below are under `/api/v1` and require the existing login session
cookie. All signed-in users have the same access; no role checks are added.
Cross-origin frontend calls must include credentials, just like existing account APIs.
Do not expose the review endpoint/service as an AI tool or give the agent a user's cookie.

| Resource | Methods |
| --- | --- |
| `/safety-rules` | GET list, POST create |
| `/safety-rules/{rule_id}` | GET detail, PUT full replacement, DELETE |
| `/ai-decisions` | GET list, POST create |
| `/ai-decisions/{decision_id}` | GET detail |
| `/command-requests` | GET list, POST propose and validate |
| `/command-requests/{request_id}` | GET detail |
| `/command-requests/{request_id}/review` | POST `{"action":"approve"}` or `{"action":"reject"}` |

JSON fields use camelCase. Lists return arrays with `limit` (1–100, default 50)
and `offset` (default 0). Rule lists accept `device_id`; decision lists accept
`schedule_id`; command lists accept `device_id`, `decision_id`, and `status`.
Use `/docs` for the complete generated request/response schemas.

Rule example:
```json
{"deviceId":"<existing UUID>","actionType":"run_for_duration","maxDurationSeconds":60,"cooldownSeconds":120,"enabled":true}
```

Command example (expiresAt must be a future timezone-aware timestamp):
```json
{"deviceId":"<existing UUID>","durationSeconds":30,"reason":"Ventilate","expiresAt":"<future ISO timestamp>"}
```

`decisionId` is optional and must reference an existing AI decision if provided.
Creation returns 201 even when the request is blocked: inspect `status` and
`resultMessage`. Review returns the resulting status, which may be blocked or
expired rather than approved. Reviewer identity comes only from the session.
Repeated review returns 409. Missing references return 404; invalid payloads
return 422; missing/invalid sessions return 401. Duplicate rules return 409.

No decision/command edit or delete API is exposed. Rules may change, but approval
rechecks current rules. The future hardware executor must revalidate immediately
before execution; approval alone is not a permanent safety guarantee.

The frontend `/logs` page lists requests and confirms reviews; `/safety` manages rules only.
It uses existing session cookies and paginates each list in groups of 20. Device
UUIDs are shown because this API does not expose a device-name directory yet.
No hardware execution or automatic AI logging integration is included.
Reads and status filters report unstarted pending/approved requests as expired
when their deadline passes, without writing during GET. Review persists expiry.
Executing or completed records keep their status. Login also checks the account
still exists. Writes load a response snapshot before commit; no refresh follows
commit. This does not provide retry idempotency for ambiguous network failures.
This code does not create/migrate database tables. Required
tables must already exist; `schema.sql` is reference documentation, not a migration.

## Frontend manual verification

- Sign in and open Safety to view rules, then Logs to view operation requests.
- Create a disabled rule with an existing device UUID; edit limits and enable it.
- Expand a pending request in Logs, approve/reject it, and verify the actual returned status (including blocked
  or expired) is displayed. Confirm no execution timestamps are created.
- Leave a pending request open past its expiry and confirm review buttons disable.
- Test rejection, duplicate review, missing device, duplicate rule, and expired login.
- Cancel a delete confirmation and verify the rule remains; confirm deletion only
  for disposable test rules. Verify pagination and refresh after another user's edit.
- Check narrow-screen layouts and keyboard navigation through both dialogs.

These checks mutate real data where noted; use designated test records. Build and
lint checks do not replace this authenticated browser/database verification.
