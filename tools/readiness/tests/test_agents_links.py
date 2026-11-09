"""Native unittest coverage for AGENTS.md link validation."""

from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_agents_links import validate_links  # noqa: E402


class AgentsLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.root = Path(self._temporary_directory.name)
        self.agents = self.root / "AGENTS.md"

    def write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_repository_agents_links_resolve(self) -> None:
        repository_agents = Path(__file__).resolve().parents[3] / "AGENTS.md"
        self.assertEqual(validate_links(repository_agents), [])

    def test_missing_local_link_fails_with_source_line(self) -> None:
        self.agents.write_text("Instructions\n\n[missing](docs/missing.md)\n", encoding="utf-8")

        self.assertEqual(
            validate_links(self.agents),
            ["AGENTS.md:3: local link 'docs/missing.md' does not exist"],
        )

    def test_external_and_code_example_links_are_not_local_references(self) -> None:
        self.agents.write_text(
            "See [external](https://example.com/docs).\n"
            "\n"
            "```markdown\n"
            "[example](docs/not-real.md)\n"
            "```\n",
            encoding="utf-8",
        )

        self.assertEqual(validate_links(self.agents), [])

    def test_link_cannot_escape_repository_root(self) -> None:
        self.agents.write_text("[outside](../outside.md)\n", encoding="utf-8")

        self.assertEqual(
            validate_links(self.agents),
            ["AGENTS.md:1: local link '../outside.md' escapes the repository"],
        )

    def test_code_labels_are_validated_but_inline_examples_are_ignored(self) -> None:
        self.agents.write_text(
            "[`missing`](docs/missing.md)\n`[example](docs/example.md)`\n",
            encoding="utf-8",
        )
        self.assertEqual(
            validate_links(self.agents),
            ["AGENTS.md:1: local link 'docs/missing.md' does not exist"],
        )

    def test_markdown_heading_fragments_are_checked(self) -> None:
        self.write("docs/guide.md", "# Setup\n\n## Setup\n")
        self.agents.write_text(
            "[second heading](docs/guide.md#setup-1)\n[missing heading](docs/guide.md#missing)\n",
            encoding="utf-8",
        )

        self.assertEqual(
            validate_links(self.agents),
            ["AGENTS.md:2: local link 'docs/guide.md#missing' has no matching heading"],
        )


if __name__ == "__main__":
    unittest.main()
