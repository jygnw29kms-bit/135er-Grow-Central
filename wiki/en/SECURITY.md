# Security

- automatic security updates
- dedicated non-login service user
- restrictive file permissions
- no direct exposure of the local port 8080
- Nginx + HTTPS on the VPS
- firewall and Fail2ban
- RBAC enforced server-side
- hashed passwords and revocable sessions
- separate API/device credentials
- secrets excluded from Git
- audit logging
- rate limiting and input validation
- remote commands disabled by default
- `DF100M_ALLOW_WRITES=false` by default
