# Changelog

All notable changes to this project are documented in this file.

---

## Translation Sync / Synchronisation des traductions

This table tracks which version each language is at. When updating one language, check if the other needs updating too.

Ce tableau indique la version de chaque langue. Lorsqu'une langue est mise a jour, verifier si l'autre doit l'etre aussi.

| Version | English (`README.md`) | Francais (`README.fr.md`) | Sync Status |
|---------|----------------------|--------------------------|-------------|
| 0.1.0-alpha | 2026-03-30 | 2026-03-30 | In sync |

### How to use / Comment utiliser

- When you update `README.md`, add a row or update the date in the English column
- When you update `README.fr.md`, add a row or update the date in the French column
- If dates differ, the older one needs updating — look at the git diff between the two dates

---

## [0.1.0-alpha] — 2026-03-30

### Added
- Two-layer architecture documentation (Commander + Control)
- 6 design patterns: Universal Worker Loop, Guardian, Circuit Breaker, MCP Abstraction, Autonomy Matrix, Dry-Run
- Adversarial Validation concept with detailed explanation
- Self-healing rules derived from production incidents
- Data strategy (RAG Memory + Blueprint)
- Self-contained demo with SQLite task broker, mock MCP server, health monitor, and worker
- Production deployment guide with scale path
- 8 lessons from production
- French translation (`README.fr.md`)
- Badge banners on both README files
- This changelog with bilingual version tracking
