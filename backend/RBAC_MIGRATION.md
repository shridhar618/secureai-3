## RBAC Migration Steps

1. Start the backend once after deploying this change.
2. On boot, the app will:
   - create the new `roles` table if it does not exist
   - add `users.role_id` if the column is missing
   - seed default enterprise roles
   - backfill each existing user from legacy `users.role` into `users.role_id`
3. Verify the data:
   - `roles` contains: `admin`, `hr`, `intern`, `developer`, `manager`, `team lead`, `finance`, `security analyst`
   - each existing user has a non-null `role_id`
4. Keep the legacy `users.role` column during the transition for backward compatibility.
5. Use the admin role API or dashboard Roles tab to create/update enterprise roles and permissions.

### API examples

`GET /api/roles`

`POST /api/roles`

```json
{
  "name": "legal",
  "permissions": {
    "allowed_intents": ["general_info", "project_info"],
    "restricted_keywords": ["salary", "password", "api key"],
    "mask_pii": false,
    "can_manage_roles": false
  }
}
```
