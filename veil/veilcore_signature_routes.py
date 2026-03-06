from fastapi import APIRouter, Query
from veil.core.signature import signed_signature_payload
from veil.core.identity import build_challenge_payload, finalize_signed_payload

router = APIRouter()

@router.get("/signature")
def veilcore_signature(component: str = "veil-api"):
    return signed_signature_payload(component=component)

@router.get("/signature/challenge")
def veilcore_signature_challenge(
    nonce: str = Query(..., min_length=8, max_length=256),
    component: str = "veil-api",
):
    base = signed_signature_payload(component=component)
    unsigned = build_challenge_payload(base=base, nonce=nonce)
    signed = finalize_signed_payload(unsigned)
    signed["eye_svg_sha16"] = signed["eye_svg_sha256"][:16]
    signed["manifest_sha16"] = signed["manifest_sha256"][:16]
    return signed
