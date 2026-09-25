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
"""Identity helpers: email normalization and the fail-closed auth policy.

Caller identity is derived exclusively from the cryptographically verified source
in :mod:`common.verified_identity`. This module intentionally no longer reads any
plaintext identity header: the prior header-fallback reader (the Vuln #4 spoofing
vector) has been removed. What remains is provider-agnostic email normalization,
shared constants, and the ``REQUIRE_AUTHENTICATED_USER`` policy resolution.
"""

import os

ANONYMOUS_USER_EMAIL = "anonymous@google.com"

LOCAL_APP_ENVS = {"", "dev", "development", "local", "test"}
TRUE_VALUES = {"1", "true", "yes", "on"}


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


def require_authenticated_user(app_env: str | None) -> bool:
    """Return whether requests without upstream identity should be rejected."""
    configured_value = os.environ.get("REQUIRE_AUTHENTICATED_USER")
    if configured_value is not None:
        return configured_value.strip().lower() in TRUE_VALUES

    return (app_env or "") not in LOCAL_APP_ENVS
