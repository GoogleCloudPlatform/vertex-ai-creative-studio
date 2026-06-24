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
"""FastAPI middleware for request identity and session state."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.responses import Response

from common.identity import ANONYMOUS_USER_EMAIL, get_authenticated_user_email
from common.storage import get_or_create_session


async def set_user_identity_and_session(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Set user identity and session information."""
    user_email = get_authenticated_user_email(request.headers)
    if not user_email:
        user_email = ANONYMOUS_USER_EMAIL

    # Get or create session ID from cookie
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    # Attach user and session info to the request state
    request.state.user_email = user_email
    request.state.session_id = session_id

    # Ensure session exists in Firestore
    get_or_create_session(session_id, user_email)

    response = await call_next(request)

    # Set session ID cookie on the response
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="Lax",
    )

    return response
