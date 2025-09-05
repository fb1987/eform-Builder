# app/main.py
import io
import json
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
from app.config import (
    ALLOWED_ORIGINS, ALLOWED_ORIGIN_REGEX, ALLOW_ALL_ORIGINS,
    EXPOSE_HEADERS, DEBUG, SERVICE_NAME
)
from app.validators import validate_and_normalize_cir
from app.composer import compose_xml
from app.pdf_outline import extract_outline_from_pdf
from app.openai_client import cir_from_description, cir_from_pdf_text

app = FastAPI(title="Ocean eForm Builder", version="0.2.0")

cors_kwargs = dict(
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=EXPOSE_HEADERS,
    max_age=86400,
)
if ALLOW_ALL_ORIGINS:
    cors_kwargs["allow_origins"] = ["*"]
elif ALLOWED_ORIGIN_REGEX:
    cors_kwargs["allow_origin_regex"] = ALLOWED_ORIGIN_REGEX
else:
    cors_kwargs["allow_origins"] = ALLOWED_ORIGINS or ["*"]
app.add_middleware(CORSMiddleware, **cors_kwargs)

@app.get("/health", tags=["meta"])
def health():
    return {"ok": True, "service": SERVICE_NAME}

def _xml_stream(xml_bytes: bytes, filename: str, issues_count: int = 0) -> StreamingResponse:
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Service": SERVICE_NAME,
        "X-Issues-Count": str(issues_count),
    }
    return StreamingResponse(io.BytesIO(xml_bytes), media_type="application/xml", headers=headers)

@app.post("/v1/create-from-description-xml", tags=["mvp"])
async def create_from_description_xml(
    description: str = Form(...),
    title: str = Form("Generated Form"),
    ref: str = Form("GeneratedForm"),
    noteType: str = Form("progress"),
    dataSecurityMode: str = Form("encrypted"),
):
    defaults = {"meta": {"title": title, "ref": ref, "noteVersion": 2, "noteType": noteType, "dataSecurityMode": dataSecurityMode}}
    cir, _raw = cir_from_description(description, defaults)
    v = validate_and_normalize_cir(cir)
    if not v["ok"]:
        raise HTTPException(status_code=400, detail={"issues": v["issues"]})
    xml_bytes = compose_xml(v["cir"])
    filename = f"{v['cir']['meta'].get('ref','form')}.xml"
    return _xml_stream(xml_bytes, filename, issues_count=len(v["issues"]))

@app.post("/v1/create-from-pdf-xml", tags=["mvp"])
async def create_from_pdf_xml(
    file: UploadFile = File(...),
    title: str = Form("Generated Form"),
    ref: str = Form("GeneratedForm"),
    noteType: str = Form("progress"),
    dataSecurityMode: str = Form("encrypted"),
):
    pdf_bytes = await file.read()
    pdf_text, _pages = extract_outline_from_pdf(pdf_bytes, file.filename)
    defaults = {"meta": {"title": title, "ref": ref, "noteVersion": 2, "noteType": noteType, "dataSecurityMode": dataSecurityMode}}
    cir, _raw = cir_from_pdf_text(pdf_text, defaults)
    v = validate_and_normalize_cir(cir)
    if not v["ok"]:
        raise HTTPException(status_code=400, detail={"issues": v["issues"]})
    xml_bytes = compose_xml(v["cir"])
    filename = f"{v['cir']['meta'].get('ref','form')}.xml"
    return _xml_stream(xml_bytes, filename, issues_count=len(v["issues"]))

@app.post("/v1/compose-xml", tags=["programmatic"])
async def compose_xml_endpoint(cir: dict):
    v = validate_and_normalize_cir(cir)
    if not v["ok"]:
        return JSONResponse({"ok": False, "issues": v["issues"]}, status_code=400)
    xml_bytes = compose_xml(v["cir"])
    return PlainTextResponse(xml_bytes.decode("utf-8"), media_type="application/xml", headers={"X-Issues-Count": str(len(v["issues"]))})

@app.post("/v1/validate-cir", tags=["programmatic"])
async def validate_cir_endpoint(cir: dict):
    v = validate_and_normalize_cir(cir)
    return {"ok": v["ok"], "issues": v["issues"], "cir": v["cir"]}
