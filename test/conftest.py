# Copyright 2025 Google LLC
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

import dataclasses
import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure dummy env vars exist for tests when running without GCP environment
os.environ.setdefault("PROJECT_ID", "test-project")
os.environ.setdefault("LOCATION", "us-central1")
os.environ.setdefault("VEO_PROJECT_ID", "test-project")
os.environ.setdefault("VEO_LOCATION", "us-central1")

# Mock parselmouth if not installed in testing environment
if "parselmouth" not in sys.modules:
    try:
        import parselmouth  # noqa: F401
    except ImportError:
        mock_pm = MagicMock()
        sys.modules["parselmouth"] = mock_pm
        sys.modules["parselmouth.praat"] = mock_pm.praat


def make_app_state(**overrides):
    """Build an ``AppState`` instance suitable for unit tests.

    ``state.state.AppState`` is a Mesop ``@me.stateclass`` whose ``__init__``
    reads the authenticated user from the active Flask request context. That
    makes it impossible to construct directly in a unit test (e.g.
    ``AppState(user_email=...)`` raises ``TypeError`` because the custom
    ``__init__`` takes no keyword arguments, and even a bare ``AppState()``
    requires a request context).

    This factory bypasses that request-bound ``__init__`` by allocating the
    instance with ``object.__new__`` and populating each declared dataclass
    field with its default value, then applying any caller-provided overrides.

    Note: only fields that declare a default (or ``default_factory``) are
    populated. Today every ``AppState`` field has a default, so the returned
    instance is fully initialized. If a future field is added without a default
    and is not supplied via ``overrides``, accessing it on the returned instance
    would raise ``AttributeError`` — pass such fields explicitly.

    Args:
        **overrides: Field values to set on the returned state. Each key must
            be a declared field of ``AppState``.

    Returns:
        An ``AppState`` instance with defaults applied and overrides set.

    Raises:
        AttributeError: If an override targets a field that ``AppState`` does
            not declare.

    """
    # Imported lazily so that collecting this module does not require the full
    # app import graph before the per-test environment is set up.
    from state.state import AppState

    field_names = {f.name for f in dataclasses.fields(AppState)}

    state = object.__new__(AppState)
    for f in dataclasses.fields(AppState):
        if f.default is not dataclasses.MISSING:
            setattr(state, f.name, f.default)
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            setattr(state, f.name, f.default_factory())

    for key, value in overrides.items():
        if key not in field_names:
            raise AttributeError(f"AppState has no field {key!r}")
        setattr(state, key, value)

    return state


@pytest.fixture
def app_state_factory():
    """Return the :func:`make_app_state` factory for tests to use."""
    return make_app_state


def pytest_addoption(parser):
    """Adds a custom command-line option to pytest for specifying the GCS bucket."""
    parser.addoption(
        "--gcs-bucket",
        action="store",
        default="gs://genai-blackbelt-fishfooding-assets",
        help="The GCS bucket to use for tests that require GCS resources.",
    )


@pytest.fixture
def gcs_bucket_for_tests(request):
    """A pytest fixture that provides the GCS bucket from the command-line option."""
    return request.config.getoption("--gcs-bucket")
