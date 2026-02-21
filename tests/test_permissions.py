"""Tests for the permission system."""

import pytest

from assistant.gateway.permissions import (
    ActionCategory,
    PermissionManager,
    classify_http_method,
    classify_shell_command,
)


def test_classify_read_commands():
    assert classify_shell_command("ls -la") == ActionCategory.READ
    assert classify_shell_command("cat file.txt") == ActionCategory.READ
    assert classify_shell_command("grep pattern file") == ActionCategory.READ
    assert classify_shell_command("pwd") == ActionCategory.READ


def test_classify_write_commands():
    assert classify_shell_command("mv a b") == ActionCategory.WRITE
    assert classify_shell_command("cp a b") == ActionCategory.WRITE
    assert classify_shell_command("python script.py") == ActionCategory.WRITE


def test_classify_delete_commands():
    assert classify_shell_command("rm file.txt") == ActionCategory.DELETE
    assert classify_shell_command("rmdir empty") == ActionCategory.DELETE


def test_classify_http():
    assert classify_http_method("GET") == ActionCategory.NETWORK_READ
    assert classify_http_method("POST") == ActionCategory.NETWORK_WRITE
    assert classify_http_method("DELETE") == ActionCategory.NETWORK_WRITE


@pytest.mark.asyncio
async def test_permission_auto_approve_read():
    async def deny_all(req):
        return False

    pm = PermissionManager(deny_all)
    allowed, req = await pm.check("shell_exec", {"command": "ls"})
    assert allowed is True  # reads are auto-approved


@pytest.mark.asyncio
async def test_permission_requires_approval():
    approved = False

    async def approve(req):
        return approved

    pm = PermissionManager(approve)
    allowed, req = await pm.check("shell_exec", {"command": "rm file.txt"})
    assert allowed is False
    assert req.requires_approval is True

    approved = True
    allowed, req = await pm.check("shell_exec", {"command": "rm file.txt"})
    assert allowed is True


@pytest.mark.asyncio
async def test_permission_read_file():
    async def deny(req):
        return False

    pm = PermissionManager(deny)
    allowed, req = await pm.check("read_file", {"path": "/tmp/test"})
    assert allowed is True  # read is auto-approved


@pytest.mark.asyncio
async def test_permission_write_file():
    async def approve(req):
        return True

    pm = PermissionManager(approve)
    allowed, req = await pm.check("write_file", {"path": "/tmp/test", "content": "x"})
    assert allowed is True
    assert req.requires_approval is True
