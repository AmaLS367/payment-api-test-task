"""Reusable OpenAPI response descriptions kept separate from route logic."""

from typing import Any

UNAUTHORIZED_RESPONSE: dict[str, Any] = {
    "description": "Authentication failed or the Bearer token is missing, invalid, or expired."
}
FORBIDDEN_RESPONSE: dict[str, Any] = {
    "description": "The authenticated user does not have administrator access."
}
NOT_FOUND_RESPONSE: dict[str, Any] = {
    "description": "The requested user or resource was not found."
}
CONFLICT_RESPONSE: dict[str, Any] = {
    "description": "The request conflicts with the current resource state."
}
VALIDATION_ERROR_RESPONSE: dict[str, Any] = {
    "description": "The request body or path parameters failed validation."
}

