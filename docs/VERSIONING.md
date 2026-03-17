# Versioning Guide

## Version Format: `MAJOR.MINOR.PATCH`

| Type | When to increment | Example |
|------|------------------|---------|
| MAJOR | Breaking changes (DB schema changes, API changes that break probe compatibility) | `1.0.0` → `2.0.0` |
| MINOR | New features, backward compatible (new dashboard page, new metric collector) | `1.0.0` → `1.1.0` |
| PATCH | Bug fixes, styling tweaks, minor improvements | `1.0.0` → `1.0.1` |

---

## How to Release a New Version

### Step 1 — Make your changes
```bash
git checkout -b feature/my-new-feature   # or fix/my-bug-fix
# ... make changes ...
git add .
git commit -m "feat: add GPU temperature to probe collector"
```

### Step 2 — Update VERSION file
```bash
echo "1.1.0" > VERSION
```

### Step 3 — Update CHANGELOG.md
Add a new section at the top under `[Unreleased]`:
```markdown
## [1.1.0] — 2025-XX-XX

### Added
- GPU temperature collector in probe
- GPU temperature chart on MachineDetail overview tab

### Fixed
- (none)

### Changed
- (none)
```

Also update the comparison link at the bottom of CHANGELOG.md:
```markdown
[1.1.0]: https://github.com/Joevikingroux/monitorpro/compare/v1.0.0...v1.1.0
```

### Step 4 — Commit and push
```bash
git add VERSION CHANGELOG.md
git commit -m "chore: release v1.1.0"
git push origin main
```

### Step 5 — GitHub Actions does the rest ✅
The `release.yml` workflow automatically:
- Creates a git tag `v1.1.0`
- Creates a GitHub Release with the changelog notes
- No manual tagging needed

---

## Commit Message Convention

Use these prefixes for clean git history:

| Prefix | Use for |
|--------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `chore:` | Version bumps, dependency updates, CI changes |
| `docs:` | Documentation only |
| `style:` | CSS/UI changes, no logic change |
| `refactor:` | Code restructure, no feature change |
| `perf:` | Performance improvement |
| `probe:` | Probe agent specific changes |

Examples:
```
feat: add per-company Telegram chat ID setting
fix: probe crash when OpenHardwareMonitor not running
style: match navbar blur to numbers10.co.za frosted glass
probe: batch offline metrics up to 10 snapshots on reconnect
chore: release v1.1.0
```

---

## Branch Strategy

```
main        ← production, always stable, protected
develop     ← integration branch, merge features here first
feature/*   ← new features branched from develop
fix/*       ← bug fixes branched from main or develop
```
