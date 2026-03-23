---
description: "Run a full build of the Quarkus project. Use when the user asks to do a full build, complete build, rebuild, or build everything."
---

Your goal is to do a full build of the local Quarkus Project.

Do the following:

1) Run `mvn install -Dquickly -Dno-test-modules -Dskip.gradle.build=true -T 16C -Prelocations` to do a quick build
