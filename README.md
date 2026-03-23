# Claude Skills

Shared [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for Java/Quarkus development.

## Skills

| Skill | Description |
|-------|-------------|
| `/decompile <ClassName>` | Decompile a Java class from Maven dependencies using CFR. Accepts fully qualified or simple class names. |
| `/classpath-search <ClassName>` | Search for a Java class across all Maven JARs. Finds which dependency provides a class, flags version conflicts. |

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/phillip-kruger/claude-skills.git ~/.claude/claude-skills
```

### 2. Symlink the commands and tools

```bash
# Create directories if needed
mkdir -p ~/.claude/commands ~/.claude/tools

# Symlink skills
ln -sf ~/.claude/claude-skills/commands/*.md ~/.claude/commands/

# Symlink tools
ln -sf ~/.claude/claude-skills/tools/* ~/.claude/tools/
chmod +x ~/.claude/tools/build-class-index.sh
```

### 3. Use them

```
> /decompile com.fasterxml.jackson.databind.ObjectMapper
> /classpath-search ObjectMapper
```

The class index is built automatically on first use and rebuilt if older than 7 days. CFR decompiler is downloaded automatically on first use.
