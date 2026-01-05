# Identity Server

A local MCP server that maintains and serves personal identity context to LLMs.

## Installation

```bash
pip install -e .
```

## Quick Start

1. Initialize your identity directory:

```bash
identity init
```

2. Edit `~/.identity/identity.yaml` with your info

3. Configure sources in `~/.identity/sources.yaml`

4. Sync your sources:

```bash
identity sync
```

5. Add to Claude Code's MCP config:

```json
{
  "mcpServers": {
    "identity": {
      "command": "identity",
      "args": ["serve"]
    }
  }
}
```

## CLI Commands

- `identity init` - Initialize identity directory
- `identity status` - Show current identity
- `identity sync` - Sync all sources
- `identity sources` - List configured sources
- `identity serve` - Start MCP server

## MCP Tools

- `get_identity()` - Core identity info
- `get_projects()` - Indexed projects
- `get_reading()` - Reading list items
- `query(question)` - Semantic search
- `list_sources()` - Configured sources
- `add_source(description)` - Setup instructions

## Source Types

- `local_files` - Markdown/text files via glob
- `git_repos` - README, commits, languages
- `rss` - RSS/Atom feeds
- `custom` - Python script connectors

## Privacy

Tag sources as `public` or `private`. Private content is excluded from MCP queries.
