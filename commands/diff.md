---
description: Show a rich, syntax-highlighted git diff in the browser. Use when the user wants to view changes, review a diff, compare branches, or see what changed in recent commits. Supports unstaged changes, staged changes, branch comparisons, and commit ranges.
---

Show a rich, syntax-highlighted git diff in the browser for: $ARGUMENTS

## Instructions

Parse the arguments to determine which diff to show, then generate an enriched HTML diff and open it in the browser.

### Argument Parsing

| User says | Git command |
|---|---|
| *(empty / no args)* | `git diff` (unstaged changes) |
| `staged` | `git diff --staged` |
| `branch <name>` | `git diff <name>...HEAD` |
| `commit HEAD~N` or `commit <sha>` | `git diff HEAD~N..HEAD` or `git show <sha>` |
| `<anything else>` | Pass directly to `git diff` as arguments |

### Step 1: Gather info

Get the branch name, diff stat, and the raw diff:

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

Run `git diff --stat` (with the appropriate arguments) to see the affected files and change counts. Also run the full `git diff` and save it to a temp file:

```bash
git diff > /tmp/claude-diff-output.patch
```

If the diff is empty, tell the user there are no changes to show and stop.

### Step 2: Write the summary JSON

Read the diff (use the Read tool on `/tmp/claude-diff-output.patch`) and create a JSON file at `/tmp/claude-diff-meta.json` with this structure:

```json
{
  "title": "Unstaged Changes",
  "branch": "fix/my-branch",
  "summary": "A 2-4 sentence summary explaining what the changes do and why. Focus on intent, not file listing. Keep it concise.",
  "files": [
    { "path": "src/main/java/com/example/Foo.java", "status": "M", "added": 13, "removed": 7 },
    { "path": "src/main/java/com/example/Bar.java", "status": "A", "added": 45, "removed": 0 }
  ]
}
```

Status values: M (modified), A (added), D (deleted), R (renamed).
Use the diff stat output to populate the `added`/`removed` counts.

### Step 3: Generate the HTML

1. Generate the diff2html content:
```bash
cat /tmp/claude-diff-output.patch | diff2html -i stdin -s side -o stdout --title "[$BRANCH] Unstaged Changes" > /tmp/claude-diff-html.html
```

2. Run the enrichment script to inject the sidebar with file tree and summary:
```bash
python3 ~/.claude/tools/diff-enrich.py /tmp/claude-diff-html.html /tmp/claude-diff-meta.json /tmp/claude-diff-view.html
```

3. Open the final file:
```bash
xdg-open /tmp/claude-diff-view.html
```

4. Clean up temp files:
```bash
rm -f /tmp/claude-diff-output.patch /tmp/claude-diff-html.html /tmp/claude-diff-meta.json
```

### Adapt title based on diff type

| Diff type | Title |
|---|---|
| Unstaged | `Unstaged Changes` |
| Staged | `Staged Changes` |
| Branch comparison | `Changes vs <branch>` |
| Commit range | `Last N commits` |
| Single commit | `<short-sha> — <commit message>` |

### Examples

- `/diff` — show unstaged changes
- `/diff staged` — show staged changes
- `/diff branch main` — compare current branch to main
- `/diff commit HEAD~3` — last 3 commits
- `/diff commit abc123` — show a specific commit
- `/diff -- src/main/java/` — diff only files in a specific directory
