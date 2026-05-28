---
name: dependency-audit
description: Audit zależności repo — CVE z npm/pip/cargo, outdated packages, license compatibility check
activation:
  patterns:
    - "dependency audit"
    - "audit dependencies"
    - "sprawdź CVE"
    - "security audit deps"
  intent_match: 0.6
requires_tools:
  - run_shell
  - file_read
  - gh_pr_comment
estimated_cost_usd: 0.40
---

# dependency-audit

Zaadaptowane z `~/projects/personal/ralph-daemon/prompts/security-audit.md`.
Cotygodniowy weryfikator (lub on-demand przed releasem).

## Inputs

- `repo` (path, required)
- `fail_on_severity` (default: `high` — `low|moderate|high|critical`)
- `licenses_blocklist` (lista, default: `["AGPL-3.0", "GPL-3.0", "SSPL-1.0"]`)
- `post_pr_comment_on` (PR URL, optional — wynik publikowany jako comment)

## Steps

1. **Detect stack:**
   - `package.json` → Node — `npm audit --json` + `npm outdated --json`
   - `requirements.txt` / `pyproject.toml` → Python — `pip-audit` + `pip list --outdated`
   - `Cargo.toml` → Rust — `cargo audit`
   - `go.mod` → Go — `govulncheck ./...`
2. Parsuj wyniki — grupuj per severity.
3. **License scan** — `license-checker` (node) / `pip-licenses` (python) → match z blocklist.
4. Wygeneruj raport:
   ```
   ## Dependency audit — {repo}

   ### 🔴 Critical (N)
   - pkg-name@version → CVE-YYYY-NNNN — affected, fix: bump to X
   ### 🟡 Outdated but no CVE (N)
   - ...
   ### ⚖️ License issues (N)
   - ...
   ```
5. Jeśli `post_pr_comment_on` set — `gh_pr_comment`.
6. Exit code = 1 jeśli któraś znaleziona vuln >= `fail_on_severity`.

## Hard limits

- Read-only audit — NIE uruchamiaj `npm audit fix` ani `cargo update` (to decyzja człowieka).
- Cache wyników 24h (advisory DBs mają rate limity).
