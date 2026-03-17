import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import yaml

from .config import CONFIG_DIR, OUTPUT_DIR


SYNC_CONFIG_PATH = CONFIG_DIR / "sync.yaml"


def load_sync_config() -> Dict:
    return yaml.safe_load(SYNC_CONFIG_PATH.read_text(encoding="utf-8")) or {}


def collect_output_files(date_str: str) -> List[Path]:
    files = []
    for subdir, suffix in [("daily", "digest"), ("topics", "topics")]:
        base = OUTPUT_DIR / subdir
        for ext in ("md", "json"):
            path = base / f"{date_str}-{suffix}.{ext}"
            if path.exists():
                files.append(path)
    return files


def sync_to_obsidian(date_str: str) -> Dict:
    cfg = load_sync_config().get("obsidian", {})
    if not cfg.get("enabled"):
        return {"status": "disabled"}

    vault_path = Path(cfg["vault_path"]).expanduser()
    target_dir = vault_path / cfg.get("target_subdir", "RSS-Daily") / date_str
    target_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for path in collect_output_files(date_str):
        if "daily" in str(path) and not cfg.get("mirror_daily", True):
            continue
        if "topics" in str(path) and not cfg.get("mirror_topics", True):
            continue
        dest = target_dir / path.name
        shutil.copy2(path, dest)
        copied.append(str(dest))

    return {"status": "ok", "target_dir": str(target_dir), "copied": copied}


def run_git(args: List[str], repo_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
    )


def detect_git_root(repo_path: Path) -> Path:
    result = run_git(["rev-parse", "--show-toplevel"], repo_path)
    if result.returncode != 0:
        return repo_path
    return Path(result.stdout.strip())



def sync_to_github(date_str: str) -> Dict:
    cfg = load_sync_config().get("github", {})
    if not cfg.get("enabled"):
        return {"status": "disabled"}

    repo_path = Path(cfg["repo_path"]).expanduser()
    git_root = detect_git_root(repo_path)
    files = collect_output_files(date_str)
    if not files:
        return {"status": "no-files"}

    rel_files = [str(path.relative_to(git_root)) for path in files if path.is_relative_to(git_root)]
    if not rel_files:
        return {"status": "no-relative-files", "git_root": str(git_root)}

    add_result = run_git(["add", *rel_files], git_root)
    staged_result = run_git(["diff", "--cached", "--name-only", "--", *rel_files], git_root)
    if add_result.returncode != 0:
        return {"status": "git-add-failed", "stderr": add_result.stderr.strip()}

    commit_result = None
    if staged_result.stdout.strip():
        message = cfg.get("commit_message_template", "chore(rss): sync outputs for {date}").format(date=date_str)
        commit_result = run_git(["commit", "-m", message, "--", *rel_files], git_root)
        if commit_result.returncode != 0:
            return {
                "status": "git-commit-failed",
                "stderr": commit_result.stderr.strip(),
                "stdout": commit_result.stdout.strip(),
                "git_root": str(git_root),
            }

    result = {
        "status": "ok" if commit_result else "clean",
        "repo_path": str(repo_path),
        "git_root": str(git_root),
        "files": rel_files,
        "commit_stdout": commit_result.stdout.strip() if commit_result else "",
    }

    if cfg.get("auto_push"):
        remote = cfg.get("remote", "origin")
        branch = cfg.get("branch", "main")
        remote_result = run_git(["remote", "get-url", remote], git_root)
        if remote_result.returncode != 0:
            result["push_status"] = "remote-missing"
            result["push_error"] = remote_result.stderr.strip() or f"remote '{remote}' not found"
            return result

        push_result = run_git(["push", remote, branch], git_root)
        if push_result.returncode != 0:
            result["push_status"] = "push-failed"
            result["push_stdout"] = push_result.stdout.strip()
            result["push_error"] = push_result.stderr.strip()
            return result

        result["push_status"] = "pushed"
        result["push_stdout"] = push_result.stdout.strip()

    return result
