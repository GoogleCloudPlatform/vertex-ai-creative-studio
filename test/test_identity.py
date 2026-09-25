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
    normalize_user_email,
    require_authenticated_user,
)
from common.verified_identity import get_verified_user_identity

# Every plaintext identity header the app historically trusted. The request path
# must NOT derive identity from any of them (Vuln #4).
SPOOFABLE_IDENTITY_HEADERS = {
    "X-Goog-Authenticated-User-Email": "accounts.google.com:iap@example.com",
    "X-Auth-Request-Email": "oauth@example.com",
    "X-Forwarded-Email": "forwarded@example.com",
    "X-Email": "spoofed@example.com",
    "X-Authenticated-User": "netskope@example.com",
}


def test_normalize_iap_email_prefix() -> None:
    assert (
        normalize_user_email("accounts.google.com:test.user@example.com")
        == "test.user@example.com"
    )


def test_deployed_request_ignores_plaintext_identity_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INVERTED (was test_uses_*_header): in a deployed env plaintext identity
    headers are never trusted. With no verified IAP assertion, the request has
    no identity regardless of any spoofed header."""
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("IAP_JWT_AUDIENCE", "test-audience")

    assert get_verified_user_identity(SPOOFABLE_IDENTITY_HEADERS) is None


def test_deployed_request_ignores_iap_email_header_without_assertion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even IAP's own *plaintext* X-Goog-Authenticated-User-Email is not an
    identity source — only the signed assertion is."""
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("IAP_JWT_AUDIENCE", "test-audience")

    headers = {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:iap@example.com",
    }

    assert get_verified_user_identity(headers) is None


def test_local_request_ignores_plaintext_identity_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In local mode too, identity comes from LOCAL_DEV_USER_EMAIL, never from a
    client-supplied plaintext header."""
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("LOCAL_DEV_USER_EMAIL", raising=False)

    assert get_verified_user_identity(SPOOFABLE_IDENTITY_HEADERS) is None


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
