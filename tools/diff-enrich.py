#!/usr/bin/env python3
"""
Enriches diff2html output with a summary header and a sidebar file tree.

Usage:
  diff-enrich.py <diff2html-file> <summary-file> <output-file>

  - diff2html-file: HTML output from `diff2html -o stdout`
  - summary-file: JSON with { "title", "branch", "summary", "files" }
    where files is [{ "path", "status", "added", "removed" }, ...]
  - output-file: Where to write the enriched HTML
"""
import json
import sys
import html


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <diff2html-file> <summary-json> <output-file>")
        sys.exit(1)

    diff2html_file, summary_file, output_file = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(diff2html_file) as f:
        diff_html = f.read()

    with open(summary_file) as f:
        meta = json.load(f)

    meta_json = json.dumps(meta)

    # The injection: CSS + a sidebar div + JS that builds the tree
    injection = '''
    <style>
      body {
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
      }
      .enriched-layout {
        display: flex !important;
        min-height: 100vh;
      }
      .enriched-sidebar {
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
      }
      .enriched-sidebar.collapsed {
        transform: translateX(-100%);
      }
      .enriched-main {
        margin-left: 380px;
        flex: 1;
        min-width: 0;
        transition: margin-left 0.25s ease;
      }
      .enriched-main.expanded {
        margin-left: 0;
      }
      .enriched-main > * {
        text-align: left !important;
      }
      .es-toggle-btn {
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
      }
      .es-toggle-btn:hover {
        background: #484f58;
        color: #c9d1d9;
      }
      .es-open-btn {
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
      }
      .es-open-btn:hover {
        background: #30363d;
        color: #c9d1d9;
      }
      .es-open-btn.visible {
        display: flex;
      }
      .es-section-title {
        margin: 0 0 10px 0;
        font-size: 11px;
        font-weight: 600;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.8px;
      }
      .es-summary {
        font-size: 13px;
        line-height: 1.6;
        color: #c9d1d9;
        margin: 0 0 20px 0;
        padding-bottom: 16px;
        border-bottom: 1px solid #30363d;
      }
      .es-summary code {
        background: #30363d;
        padding: 1px 5px;
        border-radius: 3px;
        font-size: 12px;
      }
      .es-stats {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #30363d;
        font-size: 12px;
        font-weight: 500;
        color: #8b949e;
      }
      /* Tree styles */
      .es-tree {
        font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', Menlo, monospace;
        font-size: 12px;
        line-height: 1.4;
        color: #8b949e;
      }
      .es-tree ul {
        list-style: none;
        margin: 0;
        padding: 0;
      }
      .es-tree li {
        position: relative;
        padding-left: 20px;
      }
      /* Vertical line from parent */
      .es-tree li::before {
        content: '';
        position: absolute;
        left: 6px;
        top: 0;
        height: 100%;
        border-left: 1px solid #30363d;
      }
      /* Horizontal branch line */
      .es-tree li::after {
        content: '';
        position: absolute;
        left: 6px;
        top: 11px;
        width: 10px;
        border-bottom: 1px solid #30363d;
      }
      /* Last child: cut the vertical line */
      .es-tree li:last-child::before {
        height: 11px;
      }
      /* Root level: no lines */
      .es-tree > ul > li::before,
      .es-tree > ul > li::after {
        display: none;
      }
      .es-tree > ul > li {
        padding-left: 0;
      }
      .es-tree .es-node {
        display: inline-block;
        padding: 2px 0;
        white-space: nowrap;
      }
      .es-tree .es-dir {
        color: #58a6ff;
        cursor: default;
      }
      .es-tree .es-file {
        color: #c9d1d9;
      }
      .es-tree .es-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        padding: 0 4px;
        border-radius: 3px;
        margin-right: 4px;
        line-height: 16px;
        vertical-align: middle;
      }
      .es-badge-M { background: #d29922; color: #0d1117; }
      .es-badge-A { background: #3fb950; color: #0d1117; }
      .es-badge-D { background: #f85149; color: #0d1117; }
      .es-badge-R { background: #58a6ff; color: #0d1117; }
      .es-tree .es-stats-inline {
        color: #6e7681;
        font-size: 11px;
        margin-left: 6px;
      }
      .es-tree .es-stats-inline .es-add { color: #3fb950; }
      .es-tree .es-stats-inline .es-del { color: #f85149; }
    </style>

    <script>
    document.addEventListener('DOMContentLoaded', function() {
      var META = ''' + meta_json + ''';

      // Build tree from file list
      function buildTree(files) {
        var tree = {};
        files.forEach(function(f) {
          var parts = f.path.split('/');
          var node = tree;
          for (var i = 0; i < parts.length - 1; i++) {
            if (!node[parts[i]]) node[parts[i]] = {};
            node = node[parts[i]];
          }
          node[parts[parts.length - 1]] = f;
        });
        return tree;
      }

      // Collapse single-child directory chains
      function collapseTree(tree) {
        var result = {};
        Object.keys(tree).forEach(function(name) {
          var value = tree[name];
          if (typeof value === 'object' && !value.status) {
            // Directory — try to collapse
            var chain = [name];
            var node = value;
            while (true) {
              var keys = Object.keys(node);
              if (keys.length === 1) {
                var childVal = node[keys[0]];
                if (typeof childVal === 'object' && !childVal.status) {
                  chain.push(keys[0]);
                  node = childVal;
                  continue;
                }
              }
              break;
            }
            result[chain.join('/')] = collapseTree(node);
          } else {
            result[name] = value;
          }
        });
        return result;
      }

      // Render tree as nested <ul>
      function renderTree(tree) {
        var ul = document.createElement('ul');
        Object.keys(tree).forEach(function(name) {
          var value = tree[name];
          var li = document.createElement('li');
          var span = document.createElement('span');
          span.className = 'es-node';

          if (typeof value === 'object' && !value.status) {
            // Directory
            span.innerHTML = '<span class="es-dir">' + escapeHtml(name) + '/</span>';
            li.appendChild(span);
            li.appendChild(renderTree(value));
          } else {
            // File
            var badge = '<span class="es-badge es-badge-' + value.status + '">' + value.status + '</span>';
            var stats = '';
            if (value.added || value.removed) {
              var parts = [];
              if (value.added) parts.push('<span class="es-add">+' + value.added + '</span>');
              if (value.removed) parts.push('<span class="es-del">-' + value.removed + '</span>');
              stats = '<span class="es-stats-inline">' + parts.join(' ') + '</span>';
            }
            span.innerHTML = badge + '<span class="es-file">' + escapeHtml(name) + '</span>' + stats;
            li.appendChild(span);
          }
          ul.appendChild(li);
        });
        return ul;
      }

      function escapeHtml(s) {
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
      }

      // Create sidebar
      var sidebar = document.createElement('div');
      sidebar.className = 'enriched-sidebar';

      // Close button (top-right of sidebar)
      var closeBtn = document.createElement('button');
      closeBtn.className = 'es-toggle-btn';
      closeBtn.innerHTML = '&#x2715;';
      closeBtn.title = 'Close sidebar';
      sidebar.appendChild(closeBtn);

      // Summary section
      var h3sum = document.createElement('h3');
      h3sum.className = 'es-section-title';
      h3sum.textContent = 'Summary';
      sidebar.appendChild(h3sum);

      var psum = document.createElement('p');
      psum.className = 'es-summary';
      psum.innerHTML = META.summary;
      sidebar.appendChild(psum);

      // Stats bar
      var totalAdded = 0, totalRemoved = 0;
      META.files.forEach(function(f) { totalAdded += (f.added || 0); totalRemoved += (f.removed || 0); });
      var statsDiv = document.createElement('div');
      statsDiv.className = 'es-stats';
      statsDiv.innerHTML = '<span>' + META.files.length + ' files</span> '
        + '<span style="color:#3fb950">+' + totalAdded + '</span> '
        + '<span style="color:#f85149">-' + totalRemoved + '</span>';
      sidebar.appendChild(statsDiv);

      // Tree section
      var h3tree = document.createElement('h3');
      h3tree.className = 'es-section-title';
      h3tree.textContent = 'Files Changed';
      sidebar.appendChild(h3tree);

      var treeContainer = document.createElement('div');
      treeContainer.className = 'es-tree';
      var tree = buildTree(META.files);
      var collapsed = collapseTree(tree);
      treeContainer.appendChild(renderTree(collapsed));
      sidebar.appendChild(treeContainer);

      // Wrap existing body content in main div
      var mainDiv = document.createElement('div');
      mainDiv.className = 'enriched-main';
      while (document.body.firstChild) {
        mainDiv.appendChild(document.body.firstChild);
      }

      // Open button (visible when sidebar is collapsed)
      var openBtn = document.createElement('button');
      openBtn.className = 'es-open-btn';
      openBtn.innerHTML = '&#9776;';
      openBtn.title = 'Open sidebar';

      // Toggle logic
      closeBtn.addEventListener('click', function() {
        sidebar.classList.add('collapsed');
        mainDiv.classList.add('expanded');
        openBtn.classList.add('visible');
      });
      openBtn.addEventListener('click', function() {
        sidebar.classList.remove('collapsed');
        mainDiv.classList.remove('expanded');
        openBtn.classList.remove('visible');
      });

      // Create layout wrapper
      var wrapper = document.createElement('div');
      wrapper.className = 'enriched-layout';
      wrapper.appendChild(sidebar);
      wrapper.appendChild(mainDiv);
      document.body.appendChild(wrapper);
      document.body.appendChild(openBtn);
    });
    </script>
    '''

    # Inject before </head>
    head_close = diff_html.find('</head>')
    if head_close > 0:
        enriched = diff_html[:head_close] + injection + diff_html[head_close:]
    else:
        enriched = injection + diff_html

    with open(output_file, 'w') as f:
        f.write(enriched)

    print(f"Written {len(enriched)} chars to {output_file}")


if __name__ == "__main__":
    main()
