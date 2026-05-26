---
name: hello-world
description: Reference skill showing the SKILL.md shape — says hello and explains the loader contract
activation:
  patterns:
    - "say hello"
    - "hello world"
    - "powitaj"
  intent_match: 0.5
requires_tools: []
estimated_cost_usd: 0.0
---

# hello-world

Reference skill used to verify the R1 discovery loop. Copy this directory
to `~/.ralph/skills/<your-skill>/` and edit the frontmatter to ship a real
skill.

## What this demonstrates

1. **Frontmatter parsing** — every key under `---` becomes part of the
   `Skill` descriptor returned by `ralph.skills.discover()`.
2. **Activation patterns** — `ralph.skills.match(skills, query)` returns
   this skill when the user query contains *say hello*, *hello world*, or
   *powitaj* (case-insensitive substring).
3. **Cheap LLM exposure** — only `name` and `description` go into the
   system prompt. This full body loads only when the dispatcher decides
   to run the skill (via `load_body(skill)`).

## When to write a real skill

Whenever you find yourself repeatedly explaining the same workflow to
Ralph (e.g. "generate sprint report", "fix CI", "audit deps"). A skill
turns that workflow into a one-line activation pattern + a deterministic
recipe.
