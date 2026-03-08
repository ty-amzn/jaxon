"""Tests for the skill loading system."""

from pathlib import Path

from assistant.memory.skills import SkillLoader, Skill


class TestSkillLoader:
    """Tests for the skill loading system."""

    def test_load_skills_from_empty_dir(self, tmp_path: Path):
        """Test loading from an empty directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        loader = SkillLoader(skills_dir)
        skills = loader.load_all()

        assert skills == {}
        assert loader.get_skills_prompt() == ""

    def test_load_skills_from_dir(self, tmp_path: Path):
        """Test loading skills from a directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create test skill
        skill_file = skills_dir / "test-skill.md"
        skill_file.write_text("# Test Skill\n\nThis is a test skill.")

        loader = SkillLoader(skills_dir)
        skills = loader.load_all()

        assert len(skills) == 1
        assert "test-skill" in skills
        assert skills["test-skill"].name == "test-skill"
        assert "Test Skill" in skills["test-skill"].content

    def test_get_skills_prompt(self, tmp_path: Path):
        """Test generating skills prompt."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        (skills_dir / "skill1.md").write_text("# Skill 1\nContent 1")

        loader = SkillLoader(skills_dir)
        prompt = loader.get_skills_prompt()

        assert "Available Skills" in prompt
        assert "skill1" in prompt
        assert "Content 1" in prompt

    def test_list_and_get_skills(self, tmp_path: Path):
        """Test listing and getting individual skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        (skills_dir / "alpha.md").write_text("Alpha skill")
        (skills_dir / "beta.md").write_text("Beta skill")

        loader = SkillLoader(skills_dir)
        skills = loader.list_skills()

        assert len(skills) == 2
        assert loader.get_skill("alpha") is not None
        assert loader.get_skill("nonexistent") is None

    def test_reload_skills(self, tmp_path: Path):
        """Test reloading skills from disk."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        loader = SkillLoader(skills_dir)
        assert len(loader.load_all()) == 0

        # Add a new skill after initial load
        (skills_dir / "new.md").write_text("New skill")
        loader.reload()

        assert len(loader.list_skills()) == 1
