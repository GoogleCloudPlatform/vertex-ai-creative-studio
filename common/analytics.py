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


import functools
import logging
import json
import os
import time
from contextlib import contextmanager

import mesop as me
from google.cloud import logging as cloud_logging

from state.state import AppState


class JsonFormatter(logging.Formatter):
    """Formats log records as JSON."""

    def format(self, record):
        log_object = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        # Add extra fields if they exist
        if hasattr(record, "extra_data"):
            log_object.update(record.extra_data)
        return json.dumps(log_object)


def get_logger(name: str):
    """Creates and configures a logger."""
    logger = logging.getLogger(name)
    # Prevent duplicate logs in case of multiple calls
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Check if we are in a Google Cloud environment (e.g., Cloud Run)
        if os.environ.get("K_SERVICE"):
            # The Google Cloud Logging handler automatically recognizes JSON fields
            # and parses them as structured logs.
            client = cloud_logging.Client()
            handler = client.get_default_handler()
        else:
            # For local development, use a standard handler with our custom JSON formatter.
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())

        logger.addHandler(handler)
    return logger

# Central analytics logger
analytics_logger = get_logger("genmedia.analytics")

def log_page_view(page_name: str, session_id: str = None):
    """Logs a page view event."""
    extra_data = {
        "event_type": "page_view",
        "page_name": page_name,
        "session_id": session_id,
    }
    analytics_logger.info(f"Page view: {page_name}", extra={'extra_data': extra_data})

def log_ui_click(element_id: str, page_name: str, session_id: str = None, extras: dict = None):
    """Logs a UI click event."""
    extra_data = {
        "event_type": "ui_click",
        "element_id": element_id,
        "page_name": page_name,
        "session_id": session_id,
    }
    if extras:
        extra_data.update(extras)
    analytics_logger.info(f"UI Click: {element_id} on {page_name}", extra={'extra_data': extra_data})

def log_model_call(model_name: str, status: str, duration_ms: float = 0, details: dict = None):
    """Logs a generative model call event."""
    try:
        state = me.state(AppState)
        page_name = state.current_page
        session_id = state.session_id
    except Exception:
        # Handle cases where me.state is called outside of context (e.g. threads)
        page_name = "unknown"
        session_id = "unknown"

    extra_data = {
        "event_type": "model_call",
        "model_name": model_name,
        "status": status, # e.g., "success", "failure"
        "duration_ms": round(duration_ms, 2),
        "page_name": page_name,
        "session_id": session_id,
        "details": details or {},
    }
    analytics_logger.info(f"Model Call: {model_name} ({status})", extra={'extra_data': extra_data})

def track_click(element_id: str):
    """Decorator to log a UI click event on an event handler."""
    def decorator(handler_function):
        @functools.wraps(handler_function)
        def wrapper(*args, **kwargs):
            state = me.state(AppState)
            log_ui_click(
                element_id=element_id,
                page_name=state.current_page,
                session_id=state.session_id
            )
            return handler_function(*args, **kwargs)
        return wrapper
    return decorator

@contextmanager
def track_model_call(model_name: str, **kwargs):
    """Context manager to log the duration and status of a model call."""
    start_time = time.time()
    try:
        yield
        duration_ms = (time.time() - start_time) * 1000
        log_model_call(model_name, status="success", duration_ms=duration_ms, details=kwargs)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_model_call(model_name, status="failure", duration_ms=duration_ms, details={"error": str(e), **kwargs})
        raise # Re-raise the exception after logging
