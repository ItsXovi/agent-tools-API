from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile

from app.config import settings
from app.deps import meter_conversion, rate_limit_headers_from_response, require_api_key
from app.deps import verify_admin_secret
from app.models import CreateKeyRequest, CreateKeyResponse, UsageResponse
from app.services import pdf as pdf_service
from app.services.keys import ApiKeyRecord, TIER_LIMITS, create_api_key
from app.services.pdf import PdfError, WatermarkPosition

router = APIRouter(prefix="/v1", tags=["v1"])


async def _read_upload_limited(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    max_bytes = settings.max_pdf_bytes
    while True:
        chunk = await upload.read(8192)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {max_bytes:,} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _pdf_http_error(exc: PdfError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _attachment_response(
    response: Response,
    content: bytes,
    media_type: str,
    filename: str,
) -> Response:
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        **rate_limit_headers_from_response(response),
    }
    return Response(content=content, media_type=media_type, headers=headers)


@router.post("/keys", response_model=CreateKeyResponse)
async def create_key(
    payload: CreateKeyRequest,
    _: None = Depends(verify_admin_secret),
) -> CreateKeyResponse:
    if payload.tier not in TIER_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {payload.tier}")
    raw_key, record = create_api_key(label=payload.label, tier=payload.tier)  # type: ignore[arg-type]
    return CreateKeyResponse(
        api_key=raw_key,
        key_id=record.id,
        label=record.label,
        tier=record.tier,
        limit=record.limit,
    )


@router.get("/usage", response_model=UsageResponse)
async def usage(
    record: ApiKeyRecord | None = Depends(require_api_key),
) -> UsageResponse:
    if record is None:
        return UsageResponse(
            conversions_used=0,
            limit=0,
            reset_at="",
            tier="free",
            label=None,
        )
    return UsageResponse(
        conversions_used=record.conversions_used,
        limit=record.limit,
        reset_at=record.reset_at.isoformat(),
        tier=record.tier,
        label=record.label,
    )


@router.post(
    "/pdf/merge",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def merge_pdfs(
    request: Request,
    response: Response,
    files: list[UploadFile] = File(..., description="Two or more PDF files to merge"),
    _: ApiKeyRecord | None = Depends(require_api_key),
) -> Response:
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Merge requires at least two PDF files")

    payloads: list[bytes] = []
    for upload in files:
        try:
            pdf_service.validate_pdf_filename(upload.filename)
            payloads.append(await _read_upload_limited(upload))
        except PdfError as exc:
            raise _pdf_http_error(exc) from exc

    try:
        merged = pdf_service.merge_pdfs(payloads)
    except PdfError as exc:
        raise _pdf_http_error(exc) from exc

    await meter_conversion(request, response)
    return _attachment_response(response, merged, "application/pdf", "merged.pdf")


@router.post(
    "/pdf/split",
    responses={
        200: {
            "content": {
                "application/pdf": {},
                "application/zip": {},
            }
        }
    },
)
async def split_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="PDF file to split"),
    pages: str = Query(
        ...,
        description='Page ranges (1-indexed), e.g. "1-3,5" or "all" for one PDF per page',
    ),
    _: ApiKeyRecord | None = Depends(require_api_key),
) -> Response:
    try:
        pdf_service.validate_pdf_filename(file.filename)
        data = await _read_upload_limited(file)
        output, media_type = pdf_service.split_pdf(data, pages)
    except PdfError as exc:
        raise _pdf_http_error(exc) from exc

    await meter_conversion(request, response)
    filename = "split.pdf" if media_type == "application/pdf" else "split.zip"
    return _attachment_response(response, output, media_type, filename)


@router.post(
    "/pdf/compress",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def compress_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="PDF file to compress"),
    _: ApiKeyRecord | None = Depends(require_api_key),
) -> Response:
    try:
        pdf_service.validate_pdf_filename(file.filename)
        data = await _read_upload_limited(file)
        compressed = pdf_service.compress_pdf(data)
    except PdfError as exc:
        raise _pdf_http_error(exc) from exc

    await meter_conversion(request, response)
    return _attachment_response(response, compressed, "application/pdf", "compressed.pdf")


@router.post(
    "/pdf/watermark",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def watermark_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="PDF file to watermark"),
    text: str = Query(..., description="Watermark text"),
    position: WatermarkPosition = Query(
        default="center",
        description="Watermark position: center, top, bottom, or diagonal",
    ),
    _: ApiKeyRecord | None = Depends(require_api_key),
) -> Response:
    try:
        pdf_service.validate_pdf_filename(file.filename)
        data = await _read_upload_limited(file)
        watermarked = pdf_service.watermark_pdf(data, text=text, position=position)
    except PdfError as exc:
        raise _pdf_http_error(exc) from exc

    await meter_conversion(request, response)
    return _attachment_response(response, watermarked, "application/pdf", "watermarked.pdf")
