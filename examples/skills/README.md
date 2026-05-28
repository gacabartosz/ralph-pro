# Example skills (R1 starter catalog)

Każdy folder = jeden skill w formacie `SKILL.md` z YAML frontmatter.
Loader (`src/ralph/skills.py`) discoveruje skills z dwóch lokalizacji:

- `~/.ralph/skills/<name>/SKILL.md` — global, cross-project
- `<repo>/.ralph/skills/<name>/SKILL.md` — project override (wygrywa nad global)

## Jak użyć

```bash
# Skopiuj wybrany skill do ~/.ralph/skills/
mkdir -p ~/.ralph/skills
cp -r examples/skills/jira-sprint-report ~/.ralph/skills/

# Albo wszystkie 10 startowych
cp -r examples/skills/* ~/.ralph/skills/
```

Loader podniesie je przy następnym Ralph boot. Sprawdź:

```python
from ralph import skills
for s in skills.discover():
    print(s.system_prompt_line())
```

## Katalog (R1 starter — 10 skills)

| Slot | Skill | Cel | Cost est. |
|---|---|---|---|
| R1.1 | [jira-sprint-report](./jira-sprint-report/) | Raport sprintu → Confluence draft | $0.30 |
| R1.2 | [weekly-tempo-summary](./weekly-tempo-summary/) | Godziny per osoba/projekt | $0.05 |
| R1.3 | [confluence-create-page](./confluence-create-page/) | Niskopoziomowy primitive | $0.10 |
| R1.4 | [daily-channel-summary](./daily-channel-summary/) | Slack history → decyzje + actions | $0.15 |
| R1.5 | [pr-review-checklist](./pr-review-checklist/) | Per-PR checklist z risk classification | $0.20 |
| R1.6 | [bug-investigate](./bug-investigate/) | Autonomous bug investigation (z fix + test) | $1.50 |
| R1.7 | [dependency-audit](./dependency-audit/) | CVE + outdated + license check | $0.40 |
| R1.8 | [ci-fix](./ci-fix/) | Autonomous CI failure fix | $1.00 |
| R1.9 | [code-explain](./code-explain/) | Top-down repo/file walkthrough | $0.30 |
| R1.10 | [refactor-extract-component](./refactor-extract-component/) | Frontend extract w/ props + tests | $0.60 |

Plus [hello-world](./hello-world/) jako reference (poza katalogiem R1).

## Anatomia skill

`SKILL.md` ma YAML frontmatter + markdown body:

```markdown
---
name: my-skill
description: One-liner (idzie do LLM system prompt)
activation:
  patterns:
    - "trigger phrase"
  intent_match: 0.6
requires_tools:
  - tool_name
estimated_cost_usd: 0.30
---

# my-skill

Body wyświetlony LLM-owi DOPIERO gdy activation odpali.
Tutaj opisz: Inputs, Steps, Hard limits, Output format.
```

Loader cytuje TYLKO frontmatter `name + description + activation.patterns` do system prompt (cheap). Pełen body wczytywany lazy przez `skills.load_body(skill)` gdy LLM zwraca `LOAD_SKILL: <name>`.
