# Security Audit

| Finding | Sev | Scenario | Fix |
|---------|-----|----------|-----|
| Worker heartbeat create | P0 | Attacker heartbeats arbitrary URL → job target | No create on heartbeat; validate URL |
| Empty worker secret | P0 | Register without secret if env missing | Require REGISTER_SECRET set |
| Studio unauthenticated read | P1 | Enumerate models/jobs paths | Depends(get_current_active_user) |
| Job IDOR | P1 | Read others' jobs by id | owner_id / admin check |
| Drive path traversal | P1 | dataset path `../../` | sanitize_drive_path |
| SSRF worker URL | P1 | Register metadata.google.internal | validate_worker_url (existing, enforced) |
| Skills exec | P2 | Custom code | Already disabled in production routes |
| Image paid gate | P2 | Free image abuse | can_generate_images retained |

## Not fully solved
- Postgres-backed secrets rotation
- Full CSRF for cookie sessions (JWT bearer primary)
- Artifact signed URLs
