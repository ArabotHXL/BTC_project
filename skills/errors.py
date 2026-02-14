from enum import Enum


class ErrorCode(str, Enum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_FAILED = "UPSTREAM_FAILED"
    FEATURE_DISABLED = "FEATURE_DISABLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class SkillError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict = None, http_status: int = 500):
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
        super().__init__(message)
