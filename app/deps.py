from fastapi import Header, HTTPException, Request, Response

from app.config import settings
from app.services.keys import ApiKeyRecord, METERED_PATHS, get_key_by_raw, increment_usage


def _rate_limit_headers(record: ApiKeyRecord) -> dict[str, str]:
    remaining = max(0, record.limit - record.conversions_used)
    return {
        "X-RateLimit-Limit": str(record.limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(int(record.reset_at.timestamp())),
    }


def set_rate_limit_headers(response: Response, record: ApiKeyRecord) -> None:
    for name, value in _rate_limit_headers(record).items():
        response.headers[name] = value


def rate_limit_headers_from_response(response: Response) -> dict[str, str]:
    names = ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset")
    return {name: response.headers[name] for name in names if name in response.headers}


async def require_api_key(
    request: Request,
    response: Response,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> ApiKeyRecord | None:
    if not settings.require_api_key:
        return None

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")

    record = get_key_by_raw(x_api_key)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")

    if request.method == "POST" and request.url.path in METERED_PATHS:
        if record.conversions_used >= record.limit:
            headers = _rate_limit_headers(record)
            raise HTTPException(
                status_code=429,
                detail="Monthly conversion limit exceeded",
                headers=headers,
            )

    set_rate_limit_headers(response, record)
    request.state.api_key_record = record
    return record


async def meter_conversion(
    request: Request,
    response: Response,
) -> None:
    record: ApiKeyRecord | None = getattr(request.state, "api_key_record", None)
    if record is None:
        return
    if request.method != "POST" or request.url.path not in METERED_PATHS:
        return

    updated = increment_usage(record.id)
    set_rate_limit_headers(response, updated)


def verify_admin_secret(
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
) -> None:
    if not settings.admin_secret:
        raise HTTPException(status_code=503, detail="Admin key creation is not configured")
    if x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Secret")
