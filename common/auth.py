import uuid
from fastapi import Request, Response
from common.storage import get_or_create_session

async def set_user_identity_and_session(request: Request, call_next):
    """
    FastAPI middleware to set user identity and session information.
    """
    # Get user email from header - assuming IAP
    user_email = request.headers.get("X-Goog-Authenticated-User-Email")
    if not user_email:
        # Fallback for local development or unauthenticated access
        user_email = "anonymous@google.com"

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
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite='Lax')

    return response

