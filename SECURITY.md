# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately:

1. **Do NOT** create a public GitHub issue
2. Email: [Create a private security advisory](../../security/advisories/new)
3. Include detailed description and reproduction steps

**Response Timeline:**
- Initial response: Within 48 hours
- Fix timeline provided: Within 7 days
- Security patch released: Based on severity

## Security Best Practices

When deploying this application:

- Never share your `API_SECRET_KEY`
- Use strong, randomly generated values for all secrets
- Regularly update dependencies (`pip-audit`)
- Monitor logs for security events
- Enable GitHub's security features (secret scanning, dependabot)

## Security Features

This codebase includes:

- ✅ Global API key authentication (middleware)
- ✅ SQL injection prevention (whitelisting + ORM)
- ✅ XSS protection (HTML escaping)
- ✅ IDOR protection (user validation)
- ✅ Security headers (CSP, HSTS, X-Frame-Options)
- ✅ Rate limiting (tier-based)
- ✅ Request size limiting (DoS protection)
- ✅ Timing-safe comparisons
- ✅ Error message sanitization

## Environment & Secret Protection

The following measures protect sensitive environment variables from unauthorized access:

### File System Protection
- ✅ `.env` file has restrictive permissions (`chmod 600` - owner read/write only)
- ✅ Pre-commit secret scanning config is included (install to enforce before commits)
- ✅ `.gitignore` excludes `.env` and all secret files

### AI Agent Protection
- ✅ `.opencodeignore` file prevents AI agents (OpenCode, Claude Code, etc.) from reading:
  - `.env` files
  - Key and certificate files (`*.key`, `*.pem`, `*.crt`)
  - Secrets directories
  - VSCode settings (may contain API keys)
  - Log files and databases

### Usage
```bash
# Install pre-commit hooks (recommended)
pre-commit install

# Run secret scan manually
pre-commit run --all-files

# Use the secure launcher
./run_secure.sh backend    # Start backend
./run_secure.sh bot        # Start Telegram bot

# Or run manually with environment checks
cd backend && uvicorn app.main:app --reload
```

## Acknowledgments

Security review completed February 2026.
