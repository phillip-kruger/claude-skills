---
description: "Build one or more Quarkus modules. Use when the user asks to build, compile, or rebuild specific modules. Accepts multiple module names separated by spaces or 'and' (e.g. /module-build graphql and openapi)."
---

Your goal is to build one or more modules in the Quarkus project.

The modules requested are: $ARGUMENTS

## Instructions

1. **Parse the module names.** Split `$ARGUMENTS` on spaces and the word "and" to get individual module names. For example, `graphql and openapi` means two modules: `graphql` and `openapi`.

2. **Find each module directory.** For each module name, search for a matching directory:
   ```bash
   find . -maxdepth 5 -type f -name "pom.xml" -path "*/<module-name>/*" | head -5
   ```
   Use the best match (prefer `extensions/<name>/` or `<name>/` paths).

3. **Build each module using a subagent.** For each module, use the Agent tool to dispatch a subagent that:
   - Changes to the module directory
   - Runs `mvn clean install -DskipTests`
   - Monitors the output for SUCCESS or FAILURE
   - Reports back with the result

   **Important:** If there are multiple modules, dispatch all subagents in parallel (use multiple Agent tool calls in a single response). Each subagent should have a clear prompt like:
   ```
   Build the Quarkus module at <path>. Run: cd <path> && mvn clean install -DskipTests
   Monitor the output and report whether the build succeeded or failed. If it failed, include the relevant error output.
   ```

4. **Report results.** After all subagents complete, present a summary:
   - Which modules succeeded
   - Which modules failed (with error details)
