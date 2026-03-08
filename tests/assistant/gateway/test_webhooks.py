"""Tests for webhook bearer token and template helpers."""

from assistant.gateway.webhooks import (
    verify_bearer_token,
    _extract_placeholders,
    _render_template,
)


def test_verify_bearer_token_valid():
    """Valid bearer token passes verification."""
    assert verify_bearer_token("my-secret-token", "my-secret-token") is True


def test_verify_bearer_token_invalid():
    """Invalid bearer token fails verification."""
    assert verify_bearer_token("wrong-token", "my-secret-token") is False


def test_extract_placeholders_finds_all():
    """_extract_placeholders finds all {{var}} patterns."""
    result = _extract_placeholders("Hello {{name}}, status: {{status}}, env: {{env}}")
    assert result == {"name", "status", "env"}


def test_extract_placeholders_empty():
    """_extract_placeholders returns empty set for no placeholders."""
    assert _extract_placeholders("No placeholders here") == set()


def test_extract_placeholders_duplicates():
    """_extract_placeholders deduplicates repeated placeholders."""
    result = _extract_placeholders("{{name}} and {{name}} again")
    assert result == {"name"}


def test_render_template_substitutes():
    """_render_template substitutes all placeholders with values."""
    result = _render_template(
        "Deploy {{repo}} on {{branch}} with status {{status}}",
        {"repo": "jaxon", "branch": "main", "status": "success"},
    )
    assert result == "Deploy jaxon on main with status success"


def test_render_template_leaves_unknown_placeholders():
    """_render_template leaves unmatched placeholders intact."""
    result = _render_template("Hello {{name}}, age {{age}}", {"name": "Ty"})
    assert result == "Hello Ty, age {{age}}"


def test_render_template_non_string_values():
    """_render_template converts non-string values to strings."""
    result = _render_template("Count: {{n}}, flag: {{ok}}", {"n": 42, "ok": True})
    assert result == "Count: 42, flag: True"
