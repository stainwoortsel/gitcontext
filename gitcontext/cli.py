"""Command-line interface for GitContext"""
import click
import sys
from pathlib import Path
from typing import Optional

from .core import GitContext
from .models import OTALog
from .utils import load_json


@click.group()
@click.option('--repo', default='.', help='Path to git repository')
@click.option('--llm', default='openai', help='LLM provider (openai/anthropic/ollama/deepseek/mock)')
@click.option('--model', help='LLM model name')
@click.option('--api-key', help='API key for LLM provider')
@click.pass_context
def cli(ctx, repo, llm, model, api_key):
    """GitContext - Git for AI context management"""
    ctx.ensure_object(dict)
    ctx.obj['repo'] = repo
    ctx.obj['llm'] = llm
    ctx.obj['model'] = model
    ctx.obj['api_key'] = api_key

    # Initialize GitContext
    try:
        ctx.obj['gc'] = GitContext(repo, llm, model, api_key)
    except Exception as e:
        click.echo(f"Error initializing GitContext: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize GitContext in repository"""
    try:
        ctx.obj['gc'].init()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--from', 'from_branch', help='Parent branch')
@click.pass_context
def branch(ctx, name, from_branch):
    """Create a new context branch"""
    try:
        ctx.obj['gc'].branch(name, from_branch)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('branch')
@click.pass_context
def checkout(ctx, branch):
    """Switch to a context branch"""
    try:
        ctx.obj['gc'].checkout(branch)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('message')
@click.option('--ota-file', help='JSON file with OTA logs')
@click.option('--decisions', help='Comma-separated list of decisions')
@click.pass_context
def commit(ctx, message, ota_file, decisions):
    """Commit current context"""
    try:
        # Load OTA logs if provided
        ota_logs = []
        if ota_file:
            data = load_json(Path(ota_file))
            if isinstance(data, list):
                ota_logs = [OTALog.from_dict(item) for item in data]

        # Parse decisions
        decisions_list = []
        if decisions:
            decisions_list = [d.strip() for d in decisions.split(',')]

        ctx.obj['gc'].commit(message, ota_logs, decisions_list)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('branch')
@click.option('--no-squash', is_flag=True, help='Merge without squashing')
@click.pass_context
def merge(ctx, branch, no_squash):
    """Merge a branch into current branch"""
    try:
        result = ctx.obj['gc'].merge(branch, squash=not no_squash)

        if not no_squash:
            click.echo("\n📊 Squash Summary:")
            for d in result.decisions[:3]:
                click.echo(f"  • {d[:100]}...")
            if len(result.decisions) > 3:
                click.echo(f"  ... and {len(result.decisions) - 3} more")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--branch', help='Branch to show logs from')
@click.option('--limit', default=10, help='Number of commits to show')
@click.pass_context
def log(ctx, branch, limit):
    """Show commit history"""
    try:
        commits = ctx.obj['gc'].log(branch, limit)

        if not commits:
            click.echo("No commits found")
            return

        for commit in reversed(commits):
            time_str = commit.timestamp.strftime("%Y-%m-%d %H:%M")
            click.echo(f"{click.style(commit.id[:8], fg='green')} {time_str}")
            click.echo(f"    {commit.message}")
            if commit.decisions:
                click.echo(f"    📝 {len(commit.decisions)} decisions")
            if commit.ota_logs:
                click.echo(f"    🤖 {len(commit.ota_logs)} OTA logs")
            click.echo("")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current status"""
    try:
        status = ctx.obj['gc'].status()

        click.echo(f"On branch: {click.style(status['current_branch'], fg='green')}")
        click.echo(f"Commits: {status['commits']}")

        if status['latest_commit']:
            click.echo(f"Latest: {status['latest_commit_id']} - {status['latest_commit']}")

        if status['uncommitted_changes']:
            click.echo(click.style("⚠ Uncommitted changes", fg='yellow'))

        if len(status['all_branches']) > 1:
            click.echo(f"\nBranches:")
            for b in status['all_branches']:
                marker = "*" if b == status['current_branch'] else " "
                click.echo(f"  {marker} {b}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--thought', prompt='Your thought', help='What you were thinking')
@click.option('--action', prompt='Action taken', help='What you did')
@click.option('--result', prompt='Result', help='What happened')
@click.option('--files', help='Comma-separated list of affected files')
@click.pass_context
def ota(ctx, thought, action, result, files):
    """Record an OTA (thought process) log"""
    try:
        files_list = [f.strip() for f in files.split(',')] if files else []

        log = OTALog(
            thought=thought,
            action=action,
            result=result,
            files_affected=files_list
        )

        # Save to temp file for later commit
        temp_dir = Path(ctx.obj['repo']) / '.gitcontext' / 'temp'
        temp_dir.mkdir(exist_ok=True)

        import json
        from datetime import datetime

        log_file = temp_dir / f"ota_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log.to_dict(), f, indent=2, ensure_ascii=False)

        click.echo(f"✅ OTA log saved to {log_file}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
