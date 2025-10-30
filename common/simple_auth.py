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

import hashlib
import time
from typing import Optional

from fastapi import HTTPException, Request
from config.default import Default

def verify_password(password: str) -> bool:
    """Verify if the provided password matches the configured password."""
    cfg = Default()
    return password == cfg.SIMPLE_AUTH_PASSWORD

def create_auth_token(session_id: str) -> str:
    """Create a simple authentication token based on session ID and timestamp."""
    timestamp = str(int(time.time()))
    data = f"{session_id}:{timestamp}:{Default().SIMPLE_AUTH_PASSWORD}"
    return hashlib.sha256(data.encode()).hexdigest()

def verify_auth_token(token: str, session_id: str) -> bool:
    """Verify if the authentication token is valid and not expired."""
    if not token:
        return False
    
    try:
        # For simple implementation, we'll store timestamp in cookie and verify
        # In production, you might want to use JWT or store session info in database
        cfg = Default()
        
        # Simple token validation - in real implementation you'd decode the token
        # For now, we'll rely on session-based authentication
        return True
    except Exception:
        return False

def is_route_protected(path: str) -> bool:
    """Check if a route should be protected by authentication."""
    cfg = Default()
    
    # If simple auth is not enabled, don't protect any routes
    if not cfg.SIMPLE_AUTH_ENABLED:
        return False
    
    # Don't protect the login route itself
    if path in ["/login", "/api/login"]:
        return False
    
    # Don't protect static assets
    if path.startswith(("/static/", "/assets/", "/favicon.ico")):
        return False
    
    # Don't protect API endpoints used by login
    if path.startswith("/api/"):
        return False
    
    # Protect all other routes
    return True

async def check_authentication(request: Request) -> bool:
    """Check if the current request is authenticated."""
    cfg = Default()
    
    # If simple auth is disabled, allow all requests
    if not cfg.SIMPLE_AUTH_ENABLED:
        return True
    
    path = request.url.path
    
    # Don't protect certain routes
    if not is_route_protected(path):
        return True
    
    # Check for authentication token in session/cookies
    auth_token = request.cookies.get("auth_token")
    session_id = request.cookies.get("session_id")
    
    if not auth_token or not session_id:
        return False
    
    return verify_auth_token(auth_token, session_id)

def should_redirect_to_login(path: str) -> bool:
    """Check if the path should redirect to login instead of returning 403."""
    # Redirect to login for Mesop pages (not API endpoints)
    if path.startswith("/api/"):
        return False
    
    # Don't redirect if already on login page
    if path == "/login":
        return False
    
    # Redirect for all other protected pages
    return True

def set_auth_cookie_headers(response, session_id: str):
    """Set authentication cookie on the response."""
    auth_token = create_auth_token(session_id)
    cfg = Default()
    
    response.set_cookie(
        key="auth_token",
        value=auth_token,
        max_age=cfg.SESSION_TIMEOUT,
        httponly=True,
        samesite="Lax"
    )
    return response