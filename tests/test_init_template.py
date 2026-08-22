"""Tests for ``plancritic init --template`` scaffolding (#155).

Five golden-path templates scaffold a full ``.planner-critic/`` directory:
- k8s-gitops-deploy
- secops-incident-response (→ SecOps pack)
- supply-chain-patching (→ Supply-chain pack)
- data-eng-migration (→ Data-eng pack)
- custom (interactive)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic.cli.init import (
    TEMPLATE_NAMES,
    build_init_parser,
    list_templates,
    run_init,
    run_init_template,
)


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A temp directory to scaffold into."""
    return tmp_path / "project"


class TestTemplateListing:
    def test_five_templates(self) -> None:
        assert len(TEMPLATE_NAMES) == 5
        assert "k8s-gitops-deploy" in TEMPLATE_NAMES
        assert "secops-incident-response" in TEMPLATE_NAMES
        assert "supply-chain-patching" in TEMPLATE_NAMES
        assert "data-eng-migration" in TEMPLATE_NAMES
        assert "custom" in TEMPLATE_NAMES

    def test_list_templates_returns_names(self) -> None:
        names = list_templates()
        assert isinstance(names, list)
        assert "secops-incident-response" in names


class TestRunInitTemplate:
    def test_scaffolds_secops_template(self, tmp_project: Path) -> None:
        rc = run_init_template(str(tmp_project), "secops-incident-response")
        assert rc == 0
        files = list(tmp_project.rglob("*"))
        names = {p.name for p in files}
        assert "domain_config.yaml" in names
        assert "catalog.yaml" in names
        assert "test_gates.py" in names

    def test_scaffolds_k8s_template(self, tmp_project: Path) -> None:
        rc = run_init_template(str(tmp_project), "k8s-gitops-deploy")
        assert rc == 0
        assert (tmp_project / ".planner-critic").exists()

    def test_unknown_template_fails(self, tmp_project: Path) -> None:
        rc = run_init_template(str(tmp_project), "does-not-exist")
        assert rc == 1

    def test_template_writes_gates_dir(self, tmp_project: Path) -> None:
        run_init_template(str(tmp_project), "supply-chain-patching")
        gates_dir = tmp_project / ".planner-critic" / "gates"
        assert gates_dir.exists()
        assert any(gates_dir.glob("*.py"))

    def test_idempotent_overwrite_with_force(self, tmp_project: Path) -> None:
        run_init_template(str(tmp_project), "secops-incident-response")
        rc = run_init_template(str(tmp_project), "secops-incident-response")
        assert rc == 1  # without --force it refuses
        rc2 = run_init_template(str(tmp_project), "secops-incident-response", force=True)
        assert rc2 == 0


class TestRunInitWithTemplateFlag:
    def test_parser_accepts_template_flag(self) -> None:
        parser = build_init_parser()
        args = parser.parse_args(["--template", "secops-incident-response", "--dir", "x"])
        assert args.template == "secops-incident-response"

    def test_run_init_with_template(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project.parent)
        rc = run_init(["--template", "custom", "--dir", str(tmp_project)])
        assert rc == 0
        assert (tmp_project / ".planner-critic").exists()

    def test_run_init_list_templates(self, tmp_project: Path) -> None:
        rc = run_init(["--list-templates"])
        assert rc == 0

    def test_run_init_default_still_works(self, tmp_project: Path) -> None:
        rc = run_init(["--dir", str(tmp_project)])
        assert rc == 0
        assert (tmp_project / "plancritic.toml").exists()

    def test_inject_into_existing_project(self, tmp_project: Path) -> None:
        """--inject merges template files without requiring --force."""
        run_init(["--dir", str(tmp_project)])
        # inject a template into the existing project
        rc = run_init(["--dir", str(tmp_project), "--template", "custom", "--inject"])
        assert rc == 0
        assert (tmp_project / ".planner-critic" / "gates").exists()

    def test_inject_skip_existing_files(self, tmp_project: Path) -> None:
        """--inject does not overwrite existing files without --force."""
        run_init(["--dir", str(tmp_project), "--template", "custom"])
        # Second inject with same template — files already exist without force
        rc = run_init(["--dir", str(tmp_project), "--template", "custom", "--inject"])
        assert rc == 0

    def test_inject_with_force_overwrites(self, tmp_project: Path) -> None:
        """--inject combined with --force overwrites existing files."""
        run_init(["--dir", str(tmp_project), "--template", "custom"])
        rc = run_init(
            ["--dir", str(tmp_project), "--template", "custom",
             "--inject", "--force"]
        )
        assert rc == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
