"""
VeilCore Identity + Attestation
===============================

Ed25519 node identity, manifest hashing, and signed payload helpers for:
- /signature
- /signature/challenge
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


IDENTITY_DIR = Path(os.environ.get("VEILCORE_IDENTITY_DIR", "/etc/veilcore/identity"))
PRIVATE_KEY_PATH = IDENTITY_DIR / "node_ed25519"
PUBLIC_KEY_PATH  = IDENTITY_DIR / "node_ed25519.pub"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _canonical_json_bytes(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_identity_dir() -> None:
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(IDENTITY_DIR, 0o700)
    except PermissionError:
        pass


def load_or_create_node_keypair() -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    ensure_identity_dir()

    if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
        priv = serialization.load_pem_private_key(PRIVATE_KEY_PATH.read_bytes(), password=None)
        pub = serialization.load_pem_public_key(PUBLIC_KEY_PATH.read_bytes())
        return priv, pub

    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()

    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    PRIVATE_KEY_PATH.write_bytes(priv_pem)
    PUBLIC_KEY_PATH.write_bytes(pub_pem)

    try:
        os.chmod(PRIVATE_KEY_PATH, 0o600)
        os.chmod(PUBLIC_KEY_PATH, 0o644)
    except PermissionError:
        pass

    return priv, pub


def public_key_fingerprint(pub: Ed25519PublicKey) -> str:
    raw = pub.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    return _sha256_hex(raw)[:16]


def compute_manifest(paths: Iterable[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in paths:
        path = Path(p)
        if path.exists() and path.is_file():
            out[str(path)] = _file_sha256(path)
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def manifest_hash(manifest: Dict[str, str]) -> str:
    return _sha256_hex(_canonical_json_bytes({"files": manifest}))


@dataclass(frozen=True)
class SignedPayload:
    payload: dict
    signature_b64u: str
    pubkey_fpr16: str


def sign_payload(payload: dict) -> SignedPayload:
    priv, pub = load_or_create_node_keypair()
    pubfpr = public_key_fingerprint(pub)
    sig = priv.sign(_canonical_json_bytes(payload))
    return SignedPayload(payload=payload, signature_b64u=_b64u(sig), pubkey_fpr16=pubfpr)


def finalize_signed_payload(unsigned: dict) -> dict:
    base = {k: v for k, v in unsigned.items() if k not in ("pubkey_fpr16", "sig_b64u")}
    signed = sign_payload(base)
    out = dict(signed.payload)
    out["pubkey_fpr16"] = signed.pubkey_fpr16
    out["sig_b64u"] = signed.signature_b64u
    return out


def build_signature_payload(component: str, eye_svg_sha256: str, build_id: str | None, manifest_paths: Iterable[str]) -> dict:
    node = socket.gethostname()
    manifest = compute_manifest(manifest_paths)
    mh = manifest_hash(manifest)
    return {
        "ok": True,
        "product": "VeilCore",
        "node": node,
        "component": component,
        "ts": _utc_now_z(),
        "build_id": build_id or "unknown",
        "manifest_sha256": mh,
        "files_count": len(manifest),
        "eye_svg_sha256": eye_svg_sha256,
        "pubkey_fpr16": None,
        "sig_b64u": None,
    }


def build_challenge_payload(base: dict, nonce: str) -> dict:
    return {
        "ok": True,
        "product": "VeilCore",
        "node": base.get("node"),
        "component": base.get("component"),
        "ts": _utc_now_z(),
        "build_id": base.get("build_id"),
        "manifest_sha256": base.get("manifest_sha256"),
        "eye_svg_sha256": base.get("eye_svg_sha256"),
        "nonce": nonce,
        "pubkey_fpr16": None,
        "sig_b64u": None,
    }
