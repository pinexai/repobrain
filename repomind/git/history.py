from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from git import Repo, InvalidGitRepositoryError
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class CommitRecord:
    sha: str
    author_email: str
    authored_at: str   # ISO datetime string
    message_summary: str
    files_changed: list[str]
    lines_added: int = 0
    lines_deleted: int = 0

    @property
    def lines_changed(self) -> int:
        return self.lines_added + self.lines_deleted


@dataclass
class FileHistory:
    file_path: str
    commits: list[CommitRecord] = field(default_factory=list)


class GitHistoryAnalyzer:
    """
    Analyzes git history for a repository.
    Key improvement over repowise: max_commits is FULLY CONFIGURABLE, no hardcoded 500.
    """

    def __init__(self, repo_path: Path, max_commits: int = 10_000) -> None:
        self._repo_path = repo_path
        self._max_commits = max_commits
        self._repo: Repo | None = None

    def open(self) -> bool:
        try:
            self._repo = Repo(str(self._repo_path))
            return True
        except InvalidGitRepositoryError:
            log.warning("not_a_git_repo", path=str(self._repo_path))
            return False

    def get_recent_commits(self, max_count: int | None = None) -> list[CommitRecord]:
        if not self._repo:
            return []
        limit = min(max_count or self._max_commits, self._max_commits)
        records: list[CommitRecord] = []
        try:
            for commit in self._repo.iter_commits(max_count=limit):
                files_changed: list[str] = []
                lines_added = 0
                lines_deleted = 0
                try:
                    if commit.parents:
                        diff = commit.diff(commit.parents[0])
                        for d in diff:
                            if d.a_path:
                                files_changed.append(d.a_path)
                            if d.b_path and d.b_path != d.a_path:
                                files_changed.append(d.b_path)
                        stats = commit.stats.total
                        lines_added = stats.get("insertions", 0)
                        lines_deleted = stats.get("deletions", 0)
                    else:
                        files_changed = list(commit.stats.files.keys())
                except Exception:
                    pass

                records.append(CommitRecord(
                    sha=commit.hexsha,
                    author_email=commit.author.email or "",
                    authored_at=commit.authored_datetime.isoformat(),
                    message_summary=commit.message.strip()[:200],
                    files_changed=files_changed,
                    lines_added=lines_added,
                    lines_deleted=lines_deleted,
                ))
        except Exception as e:
            log.warning("git_history_error", error=str(e))
        return records

    def get_file_history(self, file_path: str, max_count: int | None = None) -> FileHistory:
        if not self._repo:
            return FileHistory(file_path=file_path)
        limit = min(max_count or self._max_commits, self._max_commits)
        history = FileHistory(file_path=file_path)
        try:
            rel_path = str(Path(file_path).relative_to(self._repo_path))
        except ValueError:
            rel_path = file_path

        try:
            for commit in self._repo.iter_commits(paths=rel_path, max_count=limit):
                stats = commit.stats.files.get(rel_path, {})
                history.commits.append(CommitRecord(
                    sha=commit.hexsha,
                    author_email=commit.author.email or "",
                    authored_at=commit.authored_datetime.isoformat(),
                    message_summary=commit.message.strip()[:200],
                    files_changed=[rel_path],
                    lines_added=stats.get("insertions", 0),
                    lines_deleted=stats.get("deletions", 0),
                ))
        except Exception as e:
            log.warning("file_history_error", path=file_path, error=str(e))
        return history

    def close(self) -> None:
        if self._repo:
            self._repo.close()
