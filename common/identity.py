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
"""Helpers for reading authenticated user identity from trusted proxies."""

import os
from collections.abc import Mapping

ANONYMOUS_USER_EMAIL = "anonymous@google.com"

DEFAULT_AUTH_EMAIL_HEADERS = (
    "X-Goog-Authenticated-User-Email",
    "X-Auth-Request-Email",
    "X-Forwarded-Email",
    "X-Email",
    "X-Authenticated-User",
)

LOCAL_APP_ENVS = {"", "dev", "development", "local", "test"}
TRUE_VALUES = {"1", "true", "yes", "on"}


def auth_email_headers() -> tuple[str, ...]:
    """Return trusted upstream identity headers, in priority order."""
    configured_headers = os.environ.get("AUTH_EMAIL_HEADERS")
    if not configured_headers:
        return DEFAULT_AUTH_EMAIL_HEADERS

    return tuple(
        header.strip() for header in configured_headers.split(",") if header.strip()
    )


def normalize_user_email(value: str | None) -> str | None:
    """Normalize identity-provider email header formats."""
    if not value:
        return None

    user_email = value.split(",", maxsplit=1)[0].strip()
    if not user_email:
        return None

    for prefix in ("accounts.google.com:", "mailto:", "email:"):
        if user_email.lower().startswith(prefix):
            user_email = user_email[len(prefix) :].strip()
            break

    return user_email or None


def get_authenticated_user_email(
    headers: Mapping[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Read the authenticated user email from trusted request metadata."""
    for header_name in auth_email_headers():
        if headers:
            user_email = normalize_user_email(headers.get(header_name))
            if user_email:
                return user_email

        if environ:
            environ_key = f"HTTP_{header_name.upper().replace('-', '_')}"
            user_email = normalize_user_email(environ.get(environ_key))
            if user_email:
                return user_email

    if environ:
        return normalize_user_email(environ.get("MESOP_USER_EMAIL"))

    return None


def require_authenticated_user(app_env: str | None) -> bool:
    """Return whether requests without upstream identity should be rejected."""
    configured_value = os.environ.get("REQUIRE_AUTHENTICATED_USER")
    if configured_value is not None:
        return configured_value.strip().lower() in TRUE_VALUES

    return (app_env or "") not in LOCAL_APP_ENVS
