---
description: Show a rich, syntax-highlighted git diff in the browser. Use when the user wants to view changes, review a diff, compare branches, or see what changed in recent commits. Supports unstaged changes, staged changes, branch comparisons, and commit ranges. Also supports watch mode for live-updating diffs.
---

Show a rich, syntax-highlighted git diff in the browser for: $ARGUMENTS

## Instructions

### Fast mode (default)

For instant results, run the all-in-one script directly. No need to read files or generate JSON — the script handles everything (git diff, diff2html, sidebar enrichment, browser open).

| User says | Command |
|---|---|
| *(empty / no args)* | `python3 ~/.claude/tools/diff-view.py` |
| `staged` | `python3 ~/.claude/tools/diff-view.py --staged` |
| `branch <name>` | `python3 ~/.claude/tools/diff-view.py --branch <name>` |
| `commit HEAD~N` | `python3 ~/.claude/tools/diff-view.py --commit HEAD~N` |
| `commit <sha>` | `python3 ~/.claude/tools/diff-view.py --commit <sha>` |
| `watch` | `python3 ~/.claude/tools/diff-view.py --watch` |
| `watch branch main` | `python3 ~/.claude/tools/diff-view.py --watch --branch main` |
| `watch staged` | `python3 ~/.claude/tools/diff-view.py --watch --staged` |

Run the command in the background so it doesn't block the conversation:
```bash
python3 ~/.claude/tools/diff-view.py [args]
```

For watch mode, run in background:
```bash
python3 ~/.claude/tools/diff-view.py --watch [args] &
```

The sidebar will show a mechanical summary (file count and total changes). This is instant.

### AI summary mode (optional)

If the user asks for an explained diff, a summary, or review-style output, add the `--summary` flag with a Claude-generated summary:

1. Run `git diff` (with appropriate args) and read the output
2. Write a concise 2-4 sentence summary explaining the intent of the changes
3. Pass it to the script:
```bash
python3 ~/.claude/tools/diff-view.py --summary "Your AI summary here" [other args]
```

### Watch mode

When the user says `watch`, `/diff watch`, or asks for a live diff, the script:
- Regenerates the HTML every 2 seconds
- The browser auto-refreshes to show the latest diff
- Shows a green "LIVE" badge in the sidebar
- Runs until Ctrl+C

### Examples

- `/diff` — instant unstaged changes
- `/diff staged` — instant staged changes
- `/diff branch main` — compare current branch to main
- `/diff commit HEAD~3` — last 3 commits
- `/diff watch` — live-updating unstaged diff
- `/diff watch branch main` — live-updating branch comparison
