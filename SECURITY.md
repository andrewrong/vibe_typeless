# Security Guidelines

## 🔒 Preventing Secret Leakage

This project uses multiple tools to prevent accidental commit of sensitive information.

### Setup

```bash
# Install pre-commit hooks
uv add --dev pre-commit

# Install the git hooks
uv run pre-commit install

# (Optional) Run manually on all files
uv run pre-commit run --all-files
```

### Tools Used

#### 1. **detect-secrets** (Yelp)
Scans for known secret patterns (AWS keys, GitHub tokens, etc.)

```bash
# Scan for secrets
uv run detect-secrets scan > .secrets.baseline

# Audit potential secrets
uv run detect-secrets audit .secrets.baseline
```

#### 2. **Custom Pattern Checker**
Checks for common sensitive patterns in Python files:
- API keys
- Passwords
- Database URLs
- JWT tokens
- Private keys

#### 3. **Pre-commit Hooks**
Automatically runs checks before each commit.

### Best Practices

#### ✅ DO

```python
# Use environment variables
import os
api_key = os.environ.get('OPENAI_API_KEY')

# Use .env files (never commit .env!)
# .env
OPENAI_API_KEY=sk-xxx

# Python
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get('OPENAI_API_KEY')
```

#### ❌ DON'T

```python
# Hardcode secrets
api_key = "sk-abc123xyz789"  # ❌ NEVER DO THIS

# Commit .env files
# .env should be in .gitignore
```

### Files That Should Never Be Committed

```
.env                    # Environment variables
.env.local             # Local environment
.env.production        # Production secrets
*.pem                  # Private keys
*.key                  # API keys
secrets.json           # Secret configuration
credentials.json       # Credentials
```

### If You Accidentally Commit a Secret

1. **Immediately revoke the secret** at the provider (OpenAI, AWS, etc.)
2. **Remove from git history**:
   ```bash
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch path/to/file" \
   --prune-empty --tag-name-filter cat -- --all
   ```
3. **Force push** (if not shared):
   ```bash
   git push origin master --force
   ```
4. **Notify team** if the repository is shared

### CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/security.yml
name: Security Check
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run detect-secrets
        run: |
          pip install detect-secrets
          detect-secrets scan --baseline .secrets.baseline
```

### Additional Resources

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [pre-commit framework](https://pre-commit.com/)
