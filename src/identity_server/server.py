from pathlib import Path

from mcp.server.fastmcp import FastMCP

from identity_server.loader import load_identity
from identity_server.sources import load_sources
from identity_server.storage import Storage
from identity_server.embeddings import EmbeddingIndex

def create_server(identity_dir: Path) -> FastMCP:
    mcp = FastMCP("identity-server")

    # Load configs
    identity_path = identity_dir / "identity.yaml"
    sources_path = identity_dir / "sources.yaml"

    identity = load_identity(identity_path) if identity_path.exists() else None
    sources = load_sources(sources_path) if sources_path.exists() else []

    # Initialize storage
    storage = Storage(identity_dir / "index.db")
    embeddings = EmbeddingIndex(identity_dir / "embeddings.db")

    @mcp.tool()
    def get_identity() -> str:
        """Get core identity info: background, skills, current focus, interests"""
        if not identity:
            return "No identity configured"
        return _format_identity(identity)

    @mcp.tool()
    def get_projects(status: str = "active") -> str:
        """Get projects. Status: 'active', 'recent', or 'all'"""
        content = storage.get_content(source_name="projects", limit=50)
        return _format_projects(content)

    @mcp.tool()
    def get_reading(limit: int = 20) -> str:
        """Get recent reading list items"""
        content = storage.get_content(limit=limit)
        reading = [c for c in content if "rss" in c.tags]
        return _format_reading(reading)

    @mcp.tool()
    def query(question: str, sources: list[str] | None = None) -> str:
        """Natural language query across all indexed content"""
        results = embeddings.search(question, top_k=5, privacy="public")
        return _format_search_results(question, results)

    @mcp.tool()
    def list_sources() -> str:
        """List configured sources and their last sync time"""
        source_info = []
        for s in sources:
            log = storage.get_sync_log(s.name)
            source_info.append({
                "name": s.name,
                "type": s.type,
                "privacy": s.privacy,
                "last_sync": log["last_sync"] if log else "never",
            })
        return _format_sources(source_info)

    @mcp.tool()
    def add_source(description: str) -> str:
        """Get instructions for adding a new source"""
        return _add_source_instructions(description)

    return mcp

def _format_identity(identity) -> str:
    lines = [
        f"# {identity.name}",
        "",
        f"**Background:** {identity.background.summary}",
        f"**Skills:** {', '.join(identity.background.skills)}",
        "",
        "**Current Focus:**",
    ]
    for focus in identity.current_focus:
        lines.append(f"- {focus}")

    lines.append("")
    lines.append("**Interests:**")
    for interest in identity.interests:
        lines.append(f"- {interest.topic} ({interest.depth})")

    if identity.values:
        lines.append("")
        lines.append("**Values:**")
        for value in identity.values:
            lines.append(f"- {value}")

    return "\n".join(lines)

def _format_projects(content) -> str:
    if not content:
        return "No projects indexed yet."

    lines = ["# Projects", ""]
    for item in content:
        lines.append(f"## {item.title}")
        lines.append(item.body[:500])
        lines.append("")

    return "\n".join(lines)

def _format_reading(content) -> str:
    if not content:
        return "No reading items indexed yet."

    lines = ["# Recent Reading", ""]
    for item in content:
        lines.append(f"- **{item.title}**")
        if item.body:
            lines.append(f"  {item.body[:200]}...")
        lines.append("")

    return "\n".join(lines)

def _format_search_results(question: str, results) -> str:
    if not results:
        return f"No results found for: {question}"

    lines = [f"# Results for: {question}", ""]
    for item in results:
        lines.append(f"## {item.title} (from {item.source_name})")
        lines.append(item.body[:500])
        lines.append("")

    return "\n".join(lines)

def _format_sources(sources) -> str:
    if not sources:
        return "No sources configured."

    lines = ["# Configured Sources", ""]
    for s in sources:
        lines.append(f"- **{s['name']}** ({s['type']}, {s['privacy']})")
        lines.append(f"  Last sync: {s['last_sync']}")

    return "\n".join(lines)

def _add_source_instructions(description: str) -> str:
    return f"""To add a source like "{description}", edit ~/.identity/sources.yaml.

**Built-in types:**
- `local_files`: path glob (e.g., ~/notes/**/*.md)
- `git_repos`: paths to repos
- `rss`: feed URL
- `custom`: Python script connector

**Example:**
```yaml
sources:
  - name: my-source
    type: rss
    url: https://example.com/feed.xml
    privacy: public
```

For custom sources, create a connector in ~/.identity/connectors/ with a `fetch(config)` function.
"""

async def run_server(identity_dir: Path):
    mcp = create_server(identity_dir)
    await mcp.run_stdio_async()
