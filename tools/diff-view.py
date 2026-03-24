#!/usr/bin/env python3
"""
Rich browser-based git diff viewer with sidebar file tree.

Usage:
  diff-view.py [options] [-- git-diff-args...]

Modes:
  (default)              Unstaged changes
  --staged               Staged changes
  --branch <name>        Compare current branch to <name>
  --commit <ref>         Show a commit or range (e.g. HEAD~3, abc123)
  --watch                Watch for file changes and auto-refresh
  --summary <text>       AI-generated summary (optional, shown in sidebar)

Examples:
  diff-view.py                          # unstaged changes
  diff-view.py --staged                 # staged changes
  diff-view.py --branch main            # current branch vs main
  diff-view.py --commit HEAD~3          # last 3 commits
  diff-view.py --watch                  # live-updating unstaged diff
  diff-view.py --watch --branch main    # live-updating branch diff
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser


def get_branch():
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
    ).strip()


def get_git_diff(args):
    """Run git diff with the given args and return the raw diff text."""
    result = subprocess.run(
        ["git"] + args, capture_output=True, text=True
    )
    return result.stdout


def parse_numstat(args):
    """Run git diff --numstat to get per-file added/removed counts."""
    result = subprocess.run(
        ["git"] + args + ["--numstat"], capture_output=True, text=True
    )
    files = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            added = int(parts[0]) if parts[0] != "-" else 0
            removed = int(parts[1]) if parts[1] != "-" else 0
            path = parts[2]
            # Determine status
            files.append({
                "path": path,
                "added": added,
                "removed": removed,
            })
    return files


def get_file_statuses(args):
    """Run git diff --name-status to get M/A/D/R status per file."""
    result = subprocess.run(
        ["git"] + args + ["--name-status"], capture_output=True, text=True
    )
    statuses = {}
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0][0]  # First char (R100 -> R)
        path = parts[-1]  # Last part (handles renames)
        statuses[path] = status
    return statuses


def build_meta(branch, title, diff_args, summary=None):
    """Build the metadata JSON for the sidebar."""
    files = parse_numstat(diff_args)
    statuses = get_file_statuses(diff_args)

    for f in files:
        f["status"] = statuses.get(f["path"], "M")

    if summary is None:
        total_files = len(files)
        total_added = sum(f["added"] for f in files)
        total_removed = sum(f["removed"] for f in files)
        summary = f"{total_files} files changed with {total_added} additions and {total_removed} deletions."

    return {
        "title": title,
        "branch": branch,
        "summary": summary,
        "files": files,
    }


def run_diff2html(diff_text, title):
    """Run diff2html and return HTML string."""
    result = subprocess.run(
        ["diff2html", "-i", "stdin", "-s", "side", "-o", "stdout", "--title", title],
        input=diff_text, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"diff2html error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


# The CSS and JS injection for the sidebar (same as diff-enrich.py)
INJECTION_TEMPLATE = '''
    <style>
      body {{
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
      }}
      .enriched-layout {{
        display: flex !important;
        min-height: 100vh;
      }}
      .enriched-sidebar {{
        width: 380px;
        min-width: 380px;
        max-width: 380px;
        background: #161b22;
        border-right: 1px solid #30363d;
        padding: 20px;
        overflow-y: auto;
        position: fixed;
        top: 0;
        left: 0;
        height: 100vh;
        box-sizing: border-box;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        transition: transform 0.25s ease;
      }}
      .enriched-sidebar.collapsed {{
        transform: translateX(-100%);
      }}
      .enriched-main {{
        margin-left: 380px;
        flex: 1;
        min-width: 0;
        transition: margin-left 0.25s ease;
      }}
      .enriched-main.expanded {{
        margin-left: 0;
      }}
      .enriched-main > * {{
        text-align: left !important;
      }}
      .es-toggle-btn {{
        position: absolute;
        top: 8px;
        right: 8px;
        width: 28px;
        height: 28px;
        background: #30363d;
        border: 1px solid #484f58;
        border-radius: 4px;
        color: #8b949e;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        line-height: 1;
        padding: 0;
        z-index: 10000;
        transition: background 0.15s ease;
      }}
      .es-toggle-btn:hover {{
        background: #484f58;
        color: #c9d1d9;
      }}
      .es-open-btn {{
        position: fixed;
        top: 8px;
        left: 8px;
        width: 32px;
        height: 32px;
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        color: #8b949e;
        cursor: pointer;
        display: none;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        line-height: 1;
        padding: 0;
        z-index: 10000;
        transition: background 0.15s ease;
      }}
      .es-open-btn:hover {{
        background: #30363d;
        color: #c9d1d9;
      }}
      .es-open-btn.visible {{
        display: flex;
      }}
      .es-section-title {{
        margin: 0 0 10px 0;
        font-size: 11px;
        font-weight: 600;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.8px;
      }}
      .es-summary {{
        font-size: 13px;
        line-height: 1.6;
        color: #c9d1d9;
        margin: 0 0 20px 0;
        padding-bottom: 16px;
        border-bottom: 1px solid #30363d;
      }}
      .es-summary code {{
        background: #30363d;
        padding: 1px 5px;
        border-radius: 3px;
        font-size: 12px;
      }}
      .es-stats {{
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #30363d;
        font-size: 12px;
        font-weight: 500;
        color: #8b949e;
      }}
      .es-tree {{
        font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', Menlo, monospace;
        font-size: 12px;
        line-height: 1.4;
        color: #8b949e;
      }}
      .es-tree ul {{
        list-style: none;
        margin: 0;
        padding: 0;
      }}
      .es-tree li {{
        position: relative;
        padding-left: 20px;
      }}
      .es-tree li::before {{
        content: '';
        position: absolute;
        left: 6px;
        top: 0;
        height: 100%;
        border-left: 1px solid #30363d;
      }}
      .es-tree li::after {{
        content: '';
        position: absolute;
        left: 6px;
        top: 11px;
        width: 10px;
        border-bottom: 1px solid #30363d;
      }}
      .es-tree li:last-child::before {{
        height: 11px;
      }}
      .es-tree > ul > li::before,
      .es-tree > ul > li::after {{
        display: none;
      }}
      .es-tree > ul > li {{
        padding-left: 0;
      }}
      .es-tree .es-node {{
        display: inline-block;
        padding: 2px 0;
        white-space: nowrap;
      }}
      .es-tree .es-dir {{
        color: #58a6ff;
        cursor: default;
      }}
      .es-tree .es-file {{
        color: #c9d1d9;
      }}
      .es-tree .es-badge {{
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        padding: 0 4px;
        border-radius: 3px;
        margin-right: 4px;
        line-height: 16px;
        vertical-align: middle;
      }}
      .es-badge-M {{ background: #d29922; color: #0d1117; }}
      .es-badge-A {{ background: #3fb950; color: #0d1117; }}
      .es-badge-D {{ background: #f85149; color: #0d1117; }}
      .es-badge-R {{ background: #58a6ff; color: #0d1117; }}
      .es-tree .es-stats-inline {{
        color: #6e7681;
        font-size: 11px;
        margin-left: 6px;
      }}
      .es-tree .es-stats-inline .es-add {{ color: #3fb950; }}
      .es-tree .es-stats-inline .es-del {{ color: #f85149; }}
      .es-watch-badge {{
        display: inline-block;
        background: #238636;
        color: #fff;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 8px;
        letter-spacing: 0.5px;
      }}
    </style>

    <script>
    document.addEventListener('DOMContentLoaded', function() {{
      var META = {meta_json};

      function buildTree(files) {{
        var tree = {{}};
        files.forEach(function(f) {{
          var parts = f.path.split('/');
          var node = tree;
          for (var i = 0; i < parts.length - 1; i++) {{
            if (!node[parts[i]]) node[parts[i]] = {{}};
            node = node[parts[i]];
          }}
          node[parts[parts.length - 1]] = f;
        }});
        return tree;
      }}

      function collapseTree(tree) {{
        var result = {{}};
        Object.keys(tree).forEach(function(name) {{
          var value = tree[name];
          if (typeof value === 'object' && !value.status) {{
            var chain = [name];
            var node = value;
            while (true) {{
              var keys = Object.keys(node);
              if (keys.length === 1) {{
                var childVal = node[keys[0]];
                if (typeof childVal === 'object' && !childVal.status) {{
                  chain.push(keys[0]);
                  node = childVal;
                  continue;
                }}
              }}
              break;
            }}
            result[chain.join('/')] = collapseTree(node);
          }} else {{
            result[name] = value;
          }}
        }});
        return result;
      }}

      function renderTree(tree) {{
        var ul = document.createElement('ul');
        Object.keys(tree).forEach(function(name) {{
          var value = tree[name];
          var li = document.createElement('li');
          var span = document.createElement('span');
          span.className = 'es-node';
          if (typeof value === 'object' && !value.status) {{
            span.innerHTML = '<span class="es-dir">' + escapeHtml(name) + '/</span>';
            li.appendChild(span);
            li.appendChild(renderTree(value));
          }} else {{
            var badge = '<span class="es-badge es-badge-' + value.status + '">' + value.status + '</span>';
            var stats = '';
            if (value.added || value.removed) {{
              var parts = [];
              if (value.added) parts.push('<span class="es-add">+' + value.added + '</span>');
              if (value.removed) parts.push('<span class="es-del">-' + value.removed + '</span>');
              stats = '<span class="es-stats-inline">' + parts.join(' ') + '</span>';
            }}
            span.innerHTML = badge + '<span class="es-file">' + escapeHtml(name) + '</span>' + stats;
            li.appendChild(span);
          }}
          ul.appendChild(li);
        }});
        return ul;
      }}

      function escapeHtml(s) {{
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
      }}

      var sidebar = document.createElement('div');
      sidebar.className = 'enriched-sidebar';

      var closeBtn = document.createElement('button');
      closeBtn.className = 'es-toggle-btn';
      closeBtn.innerHTML = '&#x2715;';
      closeBtn.title = 'Close sidebar';
      sidebar.appendChild(closeBtn);

      if (META.summary) {{
        var h3sum = document.createElement('h3');
        h3sum.className = 'es-section-title';
        h3sum.textContent = 'Summary';
        sidebar.appendChild(h3sum);
        var psum = document.createElement('p');
        psum.className = 'es-summary';
        psum.innerHTML = META.summary;
        sidebar.appendChild(psum);
      }}

      var totalAdded = 0, totalRemoved = 0;
      META.files.forEach(function(f) {{ totalAdded += (f.added || 0); totalRemoved += (f.removed || 0); }});
      var statsDiv = document.createElement('div');
      statsDiv.className = 'es-stats';
      statsDiv.innerHTML = '<span>' + META.files.length + ' files</span> '
        + '<span style="color:#3fb950">+' + totalAdded + '</span> '
        + '<span style="color:#f85149">-' + totalRemoved + '</span>';
      sidebar.appendChild(statsDiv);

      var h3tree = document.createElement('h3');
      h3tree.className = 'es-section-title';
      h3tree.textContent = 'Files Changed';
      if (META.watching) {{
        var watchBadge = document.createElement('span');
        watchBadge.className = 'es-watch-badge';
        watchBadge.textContent = 'LIVE';
        h3tree.appendChild(watchBadge);
      }}
      sidebar.appendChild(h3tree);

      var treeContainer = document.createElement('div');
      treeContainer.className = 'es-tree';
      var tree = buildTree(META.files);
      var collapsed = collapseTree(tree);
      treeContainer.appendChild(renderTree(collapsed));
      sidebar.appendChild(treeContainer);

      var mainDiv = document.createElement('div');
      mainDiv.className = 'enriched-main';
      while (document.body.firstChild) {{
        mainDiv.appendChild(document.body.firstChild);
      }}

      var openBtn = document.createElement('button');
      openBtn.className = 'es-open-btn';
      openBtn.innerHTML = '&#9776;';
      openBtn.title = 'Open sidebar';

      closeBtn.addEventListener('click', function() {{
        sidebar.classList.add('collapsed');
        mainDiv.classList.add('expanded');
        openBtn.classList.add('visible');
      }});
      openBtn.addEventListener('click', function() {{
        sidebar.classList.remove('collapsed');
        mainDiv.classList.remove('expanded');
        openBtn.classList.remove('visible');
      }});

      var wrapper = document.createElement('div');
      wrapper.className = 'enriched-layout';
      wrapper.appendChild(sidebar);
      wrapper.appendChild(mainDiv);
      document.body.appendChild(wrapper);
      document.body.appendChild(openBtn);

      // Auto-refresh for watch mode
      if (META.watching) {{
        setInterval(function() {{ location.reload(); }}, {refresh_interval});
      }}
    }});
    </script>
    '''


def enrich_html(diff_html, meta, watching=False, refresh_ms=2000):
    """Inject sidebar CSS/JS into diff2html output."""
    meta_copy = dict(meta)
    meta_copy["watching"] = watching
    meta_json = json.dumps(meta_copy)

    injection = INJECTION_TEMPLATE.format(
        meta_json=meta_json,
        refresh_interval=refresh_ms,
    )

    head_close = diff_html.find("</head>")
    if head_close > 0:
        return diff_html[:head_close] + injection + diff_html[head_close:]
    return injection + diff_html


def generate(diff_args, title, branch, summary=None, watching=False, output_file=None):
    """Full pipeline: git diff -> diff2html -> enrich -> write file."""
    diff_text = get_git_diff(diff_args)
    if not diff_text.strip():
        return None

    full_title = f"[{branch}] {title}"
    diff_html = run_diff2html(diff_text, full_title)
    meta = build_meta(branch, title, diff_args, summary)
    enriched = enrich_html(diff_html, meta, watching=watching)

    if output_file is None:
        output_file = "/tmp/claude-diff-view.html"

    with open(output_file, "w") as f:
        f.write(enriched)

    return output_file


def watch_loop(diff_args, title, branch, summary, output_file, interval=2.0):
    """Regenerate the diff HTML every `interval` seconds."""
    print(f"Watching for changes (refresh every {interval}s). Press Ctrl+C to stop.")

    # Generate initial version and open browser
    result = generate(diff_args, title, branch, summary, watching=True, output_file=output_file)
    if result:
        webbrowser.open(f"file://{os.path.abspath(result)}")
    else:
        print("No changes to show yet. Waiting...")

    try:
        while True:
            time.sleep(interval)
            generate(diff_args, title, branch, summary, watching=True, output_file=output_file)
    except KeyboardInterrupt:
        print("\nStopped watching.")


def main():
    parser = argparse.ArgumentParser(description="Rich browser-based git diff viewer")
    parser.add_argument("--staged", action="store_true", help="Show staged changes")
    parser.add_argument("--branch", type=str, help="Compare to branch")
    parser.add_argument("--commit", type=str, help="Show commit or range")
    parser.add_argument("--watch", action="store_true", help="Watch and auto-refresh")
    parser.add_argument("--summary", type=str, default=None, help="AI summary text")
    parser.add_argument("--output", type=str, default="/tmp/claude-diff-view.html", help="Output file")
    parser.add_argument("extra", nargs="*", help="Extra git diff arguments")

    args = parser.parse_args()
    branch = get_branch()

    if args.staged:
        diff_args = ["diff", "--staged"]
        title = "Staged Changes"
    elif args.branch:
        diff_args = ["diff", f"{args.branch}...HEAD"]
        title = f"Changes vs {args.branch}"
    elif args.commit:
        ref = args.commit
        if ref.startswith("HEAD~") or ref.startswith("HEAD^"):
            diff_args = ["diff", f"{ref}..HEAD"]
            title = f"Last {ref.replace('HEAD~', '')} commits"
        else:
            diff_args = ["show", ref]
            # Get commit message
            msg = subprocess.check_output(
                ["git", "log", "-1", "--format=%s", ref], text=True
            ).strip()
            short_sha = subprocess.check_output(
                ["git", "rev-parse", "--short", ref], text=True
            ).strip()
            title = f"{short_sha} \u2014 {msg}"
    elif args.extra:
        diff_args = ["diff"] + args.extra
        title = "Diff"
    else:
        diff_args = ["diff"]
        title = "Unstaged Changes"

    if args.watch:
        watch_loop(diff_args, title, branch, args.summary, args.output)
    else:
        result = generate(diff_args, title, branch, args.summary, output_file=args.output)
        if result:
            webbrowser.open(f"file://{os.path.abspath(result)}")
            print(f"Opened {result}")
        else:
            print("No changes to show.")


if __name__ == "__main__":
    main()
