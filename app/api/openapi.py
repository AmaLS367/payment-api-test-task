"""Reusable OpenAPI response descriptions kept separate from route logic."""

UNAUTHORIZED_RESPONSE = {
    "description": "Authentication failed or the Bearer token is missing, invalid, or expired."
}
FORBIDDEN_RESPONSE = {"description": "The authenticated user does not have administrator access."}
NOT_FOUND_RESPONSE = {"description": "The requested user or resource was not found."}
CONFLICT_RESPONSE = {"description": "The request conflicts with the current resource state."}
VALIDATION_ERROR_RESPONSE = {
    "description": "The request body or path parameters failed validation."
}
