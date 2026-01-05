import asyncio
import os
from pathlib import Path

import click

from identity_server.loader import load_identity
from identity_server.sources import load_sources
from identity_server.sync import SyncManager
from identity_server.server import run_server

def get_identity_dir() -> Path:
    return Path(os.environ.get("IDENTITY_DIR", Path.home() / ".identity"))

@click.group()
def main():
    """Identity server CLI - manage your personal identity context."""
    pass

@main.command()
def status():
    """Show current identity status."""
    identity_dir = get_identity_dir()

    identity_path = identity_dir / "identity.yaml"
    if not identity_path.exists():
        click.echo(f"No identity configured at {identity_path}")
        return

    identity = load_identity(identity_path)

    click.echo(f"Name: {identity.name}")
    click.echo(f"Background: {identity.background.summary}")
    click.echo(f"Skills: {', '.join(identity.background.skills)}")
    click.echo(f"Current focus: {', '.join(identity.current_focus)}")

@main.command()
@click.option("--source", "-s", help="Sync specific source only")
def sync(source: str | None):
    """Sync all sources or a specific source."""
    identity_dir = get_identity_dir()

    sources_path = identity_dir / "sources.yaml"
    if not sources_path.exists():
        click.echo(f"No sources configured at {sources_path}")
        return

    sources = load_sources(sources_path)
    manager = SyncManager(identity_dir, sources)

    try:
        if source:
            result = manager.sync_source(source)
            click.echo(f"{source}: {result['status']} ({result.get('items', 0)} items)")
        else:
            results = manager.sync_all()
            for name, result in results.items():
                status = result["status"]
                items = result.get("items", 0)
                click.echo(f"{name}: {status} ({items} items)")

        click.echo("\nSync complete!")
    finally:
        manager.close()

@main.command()
def sources():
    """List configured sources."""
    identity_dir = get_identity_dir()

    sources_path = identity_dir / "sources.yaml"
    if not sources_path.exists():
        click.echo(f"No sources configured at {sources_path}")
        return

    source_list = load_sources(sources_path)

    if not source_list:
        click.echo("No sources configured.")
        return

    for s in source_list:
        click.echo(f"- {s.name} ({s.type}, {s.privacy})")

@main.command("init")
@click.option("--force", is_flag=True, help="Reinitialize existing directory")
def init_cmd(force: bool):
    """Initialize identity directory with example files."""
    identity_dir = get_identity_dir()

    if identity_dir.exists() and not force:
        click.echo(f"Identity directory exists at {identity_dir}")
        click.echo("Use --force to reinitialize.")
        return

    identity_dir.mkdir(parents=True, exist_ok=True)
    (identity_dir / "connectors").mkdir(exist_ok=True)

    # Create example identity.yaml
    identity_example = """# Your identity - edit this file!
name: Your Name
pronouns: they/them  # optional

background:
  summary: A brief description of who you are
  skills:
    - python
    - javascript

current_focus:
  - What you're currently working on

interests:
  - topic: programming
    depth: deep  # casual, engaged, or deep

values:
  - Things you care about

privacy:
  public:
    - name
    - background
    - interests
  private:
    - personal_notes
"""

    # Create example sources.yaml
    sources_example = """# Data sources to index
sources:
  # Example: local markdown files
  # - name: notes
  #   type: local_files
  #   path: ~/notes/**/*.md
  #   privacy: private

  # Example: git repositories
  # - name: projects
  #   type: git_repos
  #   paths:
  #     - ~/projects/*
  #   extract:
  #     - readme
  #     - recent_commits
  #   privacy: public
"""

    (identity_dir / "identity.yaml").write_text(identity_example)
    (identity_dir / "sources.yaml").write_text(sources_example)

    click.echo(f"Initialized identity directory at {identity_dir}")
    click.echo("Edit identity.yaml and sources.yaml to configure.")

@main.command()
def serve():
    """Start the MCP server."""
    identity_dir = get_identity_dir()

    if not (identity_dir / "identity.yaml").exists():
        click.echo(f"No identity configured. Run 'identity init' first.")
        return

    click.echo(f"Starting identity server from {identity_dir}")
    asyncio.run(run_server(identity_dir))

if __name__ == "__main__":
    main()
