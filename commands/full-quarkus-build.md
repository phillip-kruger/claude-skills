---
description: "Run a full build of the Quarkus project. Use when the user asks to do a full build, complete build, rebuild, or build everything."
---

Your goal is to do a full build of the local Quarkus Project.

## Instructions

1. **Use a subagent** to run the build via the Agent tool. The build can take a while, so dispatching it as a subagent keeps the main conversation responsive.

   Use this prompt for the subagent:
   ```
   Run a full Quarkus build: mvn install -Dquickly -Dno-test-modules -Dskip.gradle.build=true -T 16C -Prelocations
   Monitor the output and report whether the build succeeded or failed. If it failed, include the relevant error output.
   ```

2. **Report results.** After the subagent completes, summarize whether the build succeeded or failed.
