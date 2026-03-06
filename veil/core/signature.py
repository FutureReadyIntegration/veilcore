"""
VeilCore Signature System
========================
Author: Marlon Ástin Williams

Single source of truth:
- startup banners
- geometric eye SVG
- API signature payload (/signature)
- signed identity + manifest attestation (Ed25519)
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import os
from typing import Iterable

from veil.core.identity import finalize_signed_payload, build_signature_payload as _build_signature_payload

AUTHOR = "Marlon Ástin Williams"
MOTTO  = "Insight • Vigilance • Protection"

BUILD_ID = os.environ.get("VEILCORE_BUILD_ID", "unknown")

DEFAULT_MANIFEST_PATHS: Iterable[str] = (
    "/home/user/veilcore/veil/core/signature.py",
    "/home/user/veilcore/veil/core/identity.py",
    "/home/user/veilcore/veil/deepsentinel/service.py",
)

VEIL_EYE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="g" cx="50%" cy="45%" r="60%">
      <stop offset="0%" stop-color="#00e5ff" stop-opacity="0.95"/>
      <stop offset="55%" stop-color="#3b82f6" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#0a0e17" stop-opacity="1"/>
    </radialGradient>
  </defs>

  <rect width="512" height="512" fill="#0a0e17"/>

  <g stroke="#fbbf24" stroke-width="2" stroke-opacity="0.65">
    <line x1="256" y1="40"  x2="256" y2="112"/>
    <line x1="256" y1="400" x2="256" y2="472"/>
    <line x1="40"  y1="256" x2="112" y2="256"/>
    <line x1="400" y1="256" x2="472" y2="256"/>
    <line x1="92"  y1="92"  x2="140" y2="140"/>
    <line x1="372" y1="372" x2="420" y2="420"/>
    <line x1="372" y1="140" x2="420" y2="92"/>
    <line x1="92"  y1="420" x2="140" y2="372"/>
  </g>

  <path d="M 64 256
           C 128 160, 208 120, 256 120
           C 304 120, 384 160, 448 256
           C 384 352, 304 392, 256 392
           C 208 392, 128 352, 64 256 Z"
        fill="none" stroke="#00e5ff" stroke-width="6" stroke-opacity="0.9"/>

  <path d="M 112 256
           C 160 196, 214 176, 256 176
           C 298 176, 352 196, 400 256
           C 352 316, 298 336, 256 336
           C 214 336, 160 316, 112 256 Z"
        fill="none" stroke="#7baac4" stroke-width="3" stroke-opacity="0.75"/>

  <circle cx="256" cy="256" r="74" fill="url(#g)" stroke="#00e5ff" stroke-width="4" opacity="0.95"/>
  <circle cx="256" cy="256" r="26" fill="#0a0e17" stroke="#00e5ff" stroke-width="3" opacity="0.95"/>
  <circle cx="232" cy="238" r="10" fill="#e6f7ff" opacity="0.7"/>

  <text x="256" y="492" font-family="monospace" font-size="16" fill="#7baac4" text-anchor="middle">
    Marlon Ástin Williams
  </text>
</svg>
"""

def _fp16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def banner_text(component: str, key_fpr16: str | None = None, manifest_sha16: str | None = None) -> str:
    keyline = f"        NodeKey:   {key_fpr16}" if key_fpr16 else ""
    manline = f"        Manifest:  {manifest_sha16}" if manifest_sha16 else ""
    return f"""
========================================================
                VEILCORE DEFENSE PLATFORM
            Author: {AUTHOR}
        {MOTTO}
        Component: {component}
        Signature: {_fp16(AUTHOR + '|' + component)}
        Build:     {BUILD_ID}
{keyline}
{manline}
========================================================
""".rstrip()

def signature_payload(component: str = "veil-api") -> dict:
    # unsigned payload (compat)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return {
        "ok": True,
        "product": "VeilCore",
        "author": AUTHOR,
        "motto": MOTTO,
        "component": component,
        "ts": now,
        "signature": _fp16(AUTHOR + "|" + component),
        "svg_sha16": _fp16(VEIL_EYE_SVG),
    }

def signed_signature_payload(component: str = "veil-api") -> dict:
    eye_sha256 = _sha256_hex(VEIL_EYE_SVG)
    unsigned = _build_signature_payload(
        component=component,
        eye_svg_sha256=eye_sha256,
        build_id=BUILD_ID,
        manifest_paths=DEFAULT_MANIFEST_PATHS,
    )
    signed = finalize_signed_payload(unsigned)
    signed["eye_svg_sha16"] = signed["eye_svg_sha256"][:16]
    signed["manifest_sha16"] = signed["manifest_sha256"][:16]
    return signed

def print_signature(component: str = "veilcore", *args, **kwargs) -> None:
    try:
        if args and isinstance(args[0], str):
            component = args[0]
        component = kwargs.get("component", component)
        sp = signed_signature_payload(component=component)
        print(banner_text(component=component, key_fpr16=sp.get("pubkey_fpr16"), manifest_sha16=sp.get("manifest_sha16")))
    except Exception:
        print(banner_text(component=component))
