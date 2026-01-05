# Identity MCP Server Design

A local MCP server that maintains and serves personal identity context to LLMs.

## Goals

- **Living document**: Auto-updates via periodic scan of configured sources
- **Privacy control**: Simple public/private levels (extensible to user-defined domains later)
- **Contextual queries**: Hybrid structured tools + semantic search

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Identity Server                     │
├─────────────────────────────────────────────────────┤
│  Core Identity (curated)                            │
│  - background, values, current focus                │
│  - manually maintained YAML                         │
├─────────────────────────────────────────────────────┤
│  Source Connectors                                  │
│  - local files (notes, projects)                    │
│  - APIs (GitHub, Letterboxd, etc.)                  │
│  - RSS feeds                                        │
├─────────────────────────────────────────────────────┤
│  Index (SQLite + embeddings)                        │
│  - periodic scan updates                            │
│  - semantic search over all content                 │
├─────────────────────────────────────────────────────┤
│  MCP Tools                                          │
│  - get_identity() → core curated context            │
│  - get_projects() → current/recent work             │
│  - query("natural language") → semantic search      │
│  - add_source() → register new connector            │
└─────────────────────────────────────────────────────┘
```

## Core Identity Structure

```yaml
# identity.yaml
name: Ruthvik
pronouns: he/him  # optional

background:
  summary: "Software engineer interested in..."
  skills: [python, typescript, distributed-systems]

current_focus:
  - "Building procedural wiki generation"
  - "Exploring LLM tooling"

interests:
  - topic: film
    depth: casual  # casual | engaged | deep
  - topic: distributed-systems
    depth: deep

values:
  - "Clarity over cleverness"
  - "Build things that matter"

privacy:
  public: [name, background, interests]
  private: [personal_notes, work_details]
```

## Sources Configuration

```yaml
# sources.yaml
sources:
  # Local files
  - name: daily-notes
    type: local_files
    path: ~/notes/daily/**/*.md
    privacy: private

  - name: projects
    type: git_repos
    paths:
      - ~/projects/*
    extract: [readme, recent_commits, languages]
    privacy: public

  # External
  - name: reading-list
    type: rss
    url: https://your-reading-list-feed.xml
    privacy: public

  - name: letterboxd
    type: custom
    connector: connectors/letterboxd.py
    config:
      username: ruthvik
    privacy: public
```

**Built-in adapter types:**
- `local_files` - glob pattern, extracts text
- `git_repos` - scans READMEs, commit history, languages
- `rss` - fetches and parses feeds
- `custom` - runs user script, expects JSON output

## MCP Tools

```python
@mcp.tool()
def get_identity() -> dict:
    """Returns core curated identity - background, skills,
    current focus, interests. Always safe/fast."""

@mcp.tool()
def get_projects(status: str = "active") -> list:
    """Returns projects. Status: 'active' | 'recent' | 'all'."""

@mcp.tool()
def get_reading(limit: int = 20) -> list:
    """Returns recent reading list items."""

@mcp.tool()
def query(question: str, sources: list[str] = None) -> str:
    """Natural language query across indexed content."""

@mcp.tool()
def list_sources() -> list:
    """Lists configured sources and last sync time."""

@mcp.tool()
def add_source(description: str) -> str:
    """Describe a source to add. Returns setup instructions
    or scaffolds a custom connector."""
```

## Indexing & Search

**Storage:** SQLite with two tables:
- `content` - raw content from sources with metadata
- `embeddings` - vectors for semantic search

**Sync process** (daily or on-demand):
1. Fetch new/updated content via adapters
2. Upsert into content table
3. Generate embeddings for new entries
4. Prune stale entries

**Semantic search:**
- Local embedding model (`all-MiniLM-L6-v2` via sentence-transformers)
- No API calls, fast, private
- Returns relevant snippets with source attribution

## Directory Structure

```
~/.identity/
  identity.yaml      # core curated identity
  sources.yaml       # source configuration
  index.db           # SQLite + embeddings
  connectors/        # custom connector scripts
  sync.log           # last sync results
```

## Tech Stack

- Python + FastMCP
- SQLite + sqlite-vec for vector search
- sentence-transformers for local embeddings
- Click/Typer for CLI

## V1 Scope

**In scope:**
- MCP server with core tools
- Source connectors: local_files, git_repos, rss, custom
- SQLite index with local embeddings
- Simple public/private privacy
- CLI for manual sync

**Deferred:**
- User-defined privacy domains
- Event-driven updates
- Session summary integration
- Web UI
- Sharing/exporting identity subsets
