import shutil
import subprocess
from pathlib import Path

import pytest

from evidence import EvidenceError, Hunt, git_work_tree_for

REPO = Path(__file__).resolve().parents[5]


def test_refuses_a_git_working_tree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    if shutil.which("git"):
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
    else:
        (repo / ".git").mkdir()
    for target in (repo, repo / "evidence", repo / "deep" / "not" / "made" / "yet"):
        with pytest.raises(EvidenceError, match="git working tree"):
            Hunt(target)
    assert not (repo / "evidence").exists()
    assert not (repo / "deep").exists()


def test_refuses_this_skills_repository():
    assert git_work_tree_for(REPO / "plugins") is not None
    with pytest.raises(EvidenceError):
        Hunt(REPO / "plugins" / "research-ops" / "skills" / "source-hunter" / "evidence-test")
    assert not (REPO / "plugins" / "research-ops" / "skills" / "source-hunter" / "evidence-test").exists()


def test_refuses_a_bare_dot_git_marker(tmp_path):
    (tmp_path / "work" / ".git").mkdir(parents=True)
    with pytest.raises(EvidenceError):
        Hunt(tmp_path / "work" / "evidence")


def test_refuses_writes_that_leave_the_folder(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    with pytest.raises(EvidenceError, match="outside the evidence folder"):
        hunt.write_text("../escape.txt", "x")
    assert not (tmp_path / "escape.txt").exists()


def test_cli_refuses_git_tree(tmp_path, capsys):
    import source_hunter

    (tmp_path / "repo" / ".git").mkdir(parents=True)
    code = source_hunter.main(["report", "--evidence", str(tmp_path / "repo" / "ev")])
    assert code == 2
    assert "git working tree" in capsys.readouterr().err
    assert not (tmp_path / "repo" / "ev").exists()


def test_accepts_a_plain_folder_and_keeps_routes(tmp_path):
    hunt = Hunt(tmp_path / "evidence", name="first name")
    hunt.record_route({"route": "frame recovery", "target": "x", "status": "found"})
    again = Hunt(tmp_path / "evidence", name="second name")
    assert again.name == "first name"
    assert [r["number"] for r in again.routes()] == [1]
