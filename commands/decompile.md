---
description: Decompile a Java class from project dependencies to view its source code. Use when you need to understand a library's API, find method signatures, or explore how a dependency works internally. Accepts a fully qualified class name (e.g. com.fasterxml.jackson.databind.ObjectMapper) or a simple class name to search for.
---

Decompile and show the source code for the Java class: $ARGUMENTS

## Instructions

1. **Determine the class to decompile.** The argument is either:
   - A fully qualified class name like `com.fasterxml.jackson.databind.ObjectMapper`
   - A simple class name like `ObjectMapper` — in this case, search for it first

2. **Find the JAR containing the class.** Convert the class name to a path (replace `.` with `/`, append `.class`). Then search for it:
   ```bash
   # Build the classpath file if it doesn't exist yet
   if [ ! -f /tmp/quarkus-classpath.txt ]; then
     mvn dependency:build-classpath -Dmdep.outputFile=/tmp/quarkus-classpath.txt -q 2>/dev/null
   fi
   ```
   If the classpath file approach doesn't find it, search the Maven local repo directly:
   ```bash
   find ~/.m2/repository -name "*.jar" -exec jar -tf {} \; 2>/dev/null | grep "ClassName.class"
   ```
   Or more efficiently:
   ```bash
   # Find JARs that might contain the class based on groupId/artifactId hints
   find ~/.m2/repository -name "*.jar" | while read jar; do
     if jar tf "$jar" 2>/dev/null | grep -q "path/to/ClassName.class"; then
       echo "$jar"
       break
     fi
   done
   ```

3. **Ensure CFR decompiler is available:**
   ```bash
   CFR_JAR="$HOME/.claude/tools/cfr.jar"
   if [ ! -f "$CFR_JAR" ]; then
     mkdir -p "$HOME/.claude/tools"
     curl -sL "https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar" -o "$CFR_JAR"
   fi
   ```

4. **Decompile the class** using CFR:
   ```bash
   java -jar "$HOME/.claude/tools/cfr.jar" "fully.qualified.ClassName" --extraclasspath "/path/to/the.jar"
   ```

   If CFR fails, fall back to javap:
   ```bash
   javap -p -c -cp "/path/to/the.jar" "fully.qualified.ClassName"
   ```

5. **Present the decompiled source** to the user with syntax highlighting context. Highlight:
   - Public API methods and their signatures
   - Constructor parameters
   - Important fields
   - Any relevant annotations

6. If the user provided a simple class name and multiple matches exist, list them and ask which one to decompile.

## Tips
- For Quarkus internal classes, they may be in the local build output (`target/classes/`) rather than in `.m2`
- The `--extraclasspath` flag in CFR can take multiple JARs separated by `:` (or `;` on Windows)
- Use `jar tf some.jar | grep -i ClassName` to search within a specific JAR
