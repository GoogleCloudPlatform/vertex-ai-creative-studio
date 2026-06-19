# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for trusted proxy identity helpers."""

# ruff: noqa: D103, S101

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.identity import (
    ANONYMOUS_USER_EMAIL,
    auth_email_headers,
    get_authenticated_user_email,
    normalize_user_email,
    require_authenticated_user,
)


def test_normalize_iap_email_prefix() -> None:
    assert (
        normalize_user_email("accounts.google.com:test.user@example.com")
        == "test.user@example.com"
    )


def test_uses_iap_header_before_proxy_headers() -> None:
    headers = {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:iap@example.com",
        "X-Auth-Request-Email": "oauth@example.com",
    }

    assert get_authenticated_user_email(headers=headers) == "iap@example.com"


def test_uses_oauth2_proxy_email_header() -> None:
    headers = {"X-Auth-Request-Email": "oauth@example.com"}

    assert get_authenticated_user_email(headers=headers) == "oauth@example.com"


def test_uses_netskope_authenticated_user_header() -> None:
    headers = {"X-Authenticated-User": "netskope@example.com"}

    assert get_authenticated_user_email(headers=headers) == "netskope@example.com"


def test_reads_wsgi_environ_header() -> None:
    environ = {"HTTP_X_FORWARDED_EMAIL": "forwarded@example.com"}

    assert get_authenticated_user_email(environ=environ) == "forwarded@example.com"


def test_custom_auth_email_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_EMAIL_HEADERS", "X-Custom-Email")

    assert auth_email_headers() == ("X-Custom-Email",)
    assert (
        get_authenticated_user_email(headers={"X-Custom-Email": "custom@example.com"})
        == "custom@example.com"
    )


def test_require_authenticated_user_is_false_for_local_envs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REQUIRE_AUTHENTICATED_USER", raising=False)

    assert not require_authenticated_user("local")
    assert not require_authenticated_user("")


def test_require_authenticated_user_is_true_for_prod_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REQUIRE_AUTHENTICATED_USER", raising=False)

    assert require_authenticated_user("prod")


def test_require_authenticated_user_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REQUIRE_AUTHENTICATED_USER", "false")

    assert not require_authenticated_user("prod")

    monkeypatch.setenv("REQUIRE_AUTHENTICATED_USER", "true")

    assert require_authenticated_user("")


def test_anonymous_user_constant_matches_existing_default() -> None:
    assert ANONYMOUS_USER_EMAIL == "anonymous@google.com"
