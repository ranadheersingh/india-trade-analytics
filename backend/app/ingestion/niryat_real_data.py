"""
DGFT eBRC IEC Integration System
==================================
Implements the full 3-layer auth spec (v1.3, Jan 2026):

  Step 1 — getAccessToken
    POST https://apiservices.dgft.gov.in/genebrc/getAccessToken
    Header: x-api-key, Content-Type: application/json
    Body:   {"client_id": "...", "client_secret": "<base64(32-byte-salt + PBKDF2-SHA256-hash)>"}

  Step 2 — fetchEBRCDetails
    POST https://apiservices.dgft.gov.in/genebrc/fetchEBRCDetails
    Headers: accessToken, client_id, secretVal (RSA-OAEP-SHA256 encrypted AES key)
    Body:   {"data": "<b64(IV+salt+AES-GCM-ciphertext)>", "sign": "<RSA-SHA256-sig>"}

Credential fields (all from downloaded credentials*.txt on DGFT portal):
  DGFT_CLIENT_ID, DGFT_CLIENT_SECRET, DGFT_X_API_KEY,
  DGFT_PRIVATE_KEY  (user's PKCS8 DER private key, base64)
  DGFT_PUBLIC_KEY   (DGFT server's X509 DER public key, base64) — needed for secretVal
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import string
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.config import get_settings
from app.models import (
    DimExporter, DimCountry, DimHsCode, DimDate, DimPort, DimTransportMode,
    FactExportTransaction,
)

logger = logging.getLogger(__name__)

DGFT_BASE   = "https://apiservices.dgft.gov.in/genebrc"
TOKEN_URL   = f"{DGFT_BASE}/getAccessToken"
EBRC_URL    = f"{DGFT_BASE}/fetchEBRCDetails"
IRM_URL     = f"{DGFT_BASE}/fetchIRMDetails"


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------

def _pbkdf2_secret(client_secret: str) -> str:
    """
    Hash client_secret per DGFT spec:
      salt  = 32 random bytes
      hash  = PBKDF2-HMAC-SHA256(password, salt, 65536 iter, 32-byte key)
      return = base64(salt + hash)
    """
    salt = os.urandom(32)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=65536)
    key_bytes = kdf.derive(client_secret.encode("utf-8"))
    return base64.b64encode(salt + key_bytes).decode("utf-8")


def _random_plain_key(length: int = 32) -> str:
    """Generate a random keyboard-character key for AES."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    return "".join(secrets.choice(chars) for _ in range(length))


def _encrypt_payload(payload: dict) -> Tuple[str, str, str]:
    """
    Encrypt payload per DGFT spec sections 3.1 / 3.3.

    Returns:
        data_b64   — base64(12-byte IV + 32-byte salt + AES-GCM ciphertext+tag)
        json_b64   — base64(original JSON string), used for signing
        plain_key  — 32-char secret key, caller must encrypt it for secretVal header
    """
    # Step 1: JSON → base64
    json_str = json.dumps(payload, separators=(",", ":"))
    json_b64 = base64.b64encode(json_str.encode("utf-8"))

    # Step 2: generate 32-char plain text secret key
    plain_key = _random_plain_key(32)

    # Step 3: IV = first 12 bytes of secret key (per algo spec)
    iv = plain_key[:12].encode("utf-8")

    # Step 4: derive AES-256 key = SHA256(secret_key_bytes + salt)
    salt = os.urandom(32)
    aes_key = hashlib.sha256(plain_key.encode("utf-8") + salt).digest()  # 32 bytes

    # Step 5: AES-256-GCM encrypt (produces ciphertext + 16-byte GCM tag)
    aesgcm = AESGCM(aes_key)
    ciphertext_tag = aesgcm.encrypt(iv, json_b64, None)

    # data = base64(IV + salt + ciphertext_tag)
    data_b64 = base64.b64encode(iv + salt + ciphertext_tag).decode("utf-8")

    return data_b64, json_b64.decode("utf-8"), plain_key


def _sign_message(json_b64: str, private_key_b64: str) -> str:
    """RSA-SHA256 digital signature over base64-encoded message."""
    raw = base64.b64decode(private_key_b64)
    private_key = serialization.load_der_private_key(raw, password=None)
    sig = private_key.sign(json_b64.encode("utf-8"), asym_padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode("utf-8")


def _encrypt_aes_key(plain_key: str, dgft_public_key_b64: str) -> str:
    """Encrypt AES plain_key with DGFT's RSA public key (OAEP-SHA256-MFG1)."""
    raw = base64.b64decode(dgft_public_key_b64)
    try:
        public_key = serialization.load_der_public_key(raw)
    except Exception:
        # Try SubjectPublicKeyInfo (X509) format
        public_key = serialization.load_pem_public_key(
            b"-----BEGIN PUBLIC KEY-----\n" +
            base64.encodebytes(raw) +
            b"-----END PUBLIC KEY-----\n"
        )
    encrypted = public_key.encrypt(
        plain_key.encode("utf-8"),
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(encrypted).decode("utf-8")


# ---------------------------------------------------------------------------
# Auth client
# ---------------------------------------------------------------------------

class DGFTAuthClient:
    """Manages DGFT access token lifecycle."""

    def __init__(self):
        s = get_settings()
        self.client_id      = s.dgft_client_id
        self.client_secret  = s.dgft_client_secret
        self.x_api_key      = s.dgft_x_api_key
        self.private_key    = s.dgft_private_key
        self.public_key     = s.dgft_public_key   # DGFT server public key

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.x_api_key)

    def get_token(self) -> Optional[str]:
        """
        Fetch access token using PBKDF2-hashed client_secret.
        Token expires in 5 minutes; caller should refresh per request.
        """
        if not self.is_configured():
            logger.warning("DGFT credentials not configured — set DGFT_CLIENT_ID/SECRET/X_API_KEY")
            return None
        hashed = _pbkdf2_secret(self.client_secret)
        try:
            resp = httpx.post(
                TOKEN_URL,
                json={"client_id": self.client_id, "client_secret": hashed},
                headers={"Content-Type": "application/json", "x-api-key": self.x_api_key},
                timeout=30,
            )
            resp.raise_for_status()
            token = resp.json().get("accessToken")
            logger.info("DGFT access token acquired (expires in 300s)")
            return token
        except httpx.HTTPStatusError as e:
            logger.error("DGFT token HTTP %s: %s", e.response.status_code, e.response.text[:300])
        except Exception as e:
            logger.error("DGFT token error: %s", e)
        return None

    def build_encrypted_request(self, payload: dict) -> Tuple[dict, dict]:
        """
        Encrypt payload and build (body, extra_headers) for a data API call.
        Returns ({data, sign}, {secretVal, accessToken, client_id}).
        Returns (None, None) if private key or DGFT public key are missing.
        """
        if not self.private_key:
            logger.warning("DGFT_PRIVATE_KEY not set — cannot sign requests")
            return None, None
        if not self.public_key:
            logger.warning(
                "DGFT_PUBLIC_KEY not set — cannot encrypt secretVal. "
                "Download credentials from DGFT portal: Services > eBRC > API Credential "
                "and set DGFT_PUBLIC_KEY from the dgftpublicKey field."
            )
            return None, None

        token = self.get_token()
        if not token:
            return None, None

        data_b64, json_b64, plain_key = _encrypt_payload(payload)
        sign = _sign_message(json_b64, self.private_key)
        secret_val = _encrypt_aes_key(plain_key, self.public_key)

        body = {"data": data_b64, "sign": sign}
        headers = {
            "Content-Type": "application/json",
            "accessToken": token,
            "client_id": self.client_id,
            "secretVal": secret_val,
        }
        return body, headers


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class NIRYATAPIClient:
    """Fetches eBRC data from DGFT fetchEBRCDetails API."""

    def __init__(self):
        self.auth = DGFTAuthClient()
        self.iec_code = get_settings().dgft_iec_code or "AXGPK0287Q"

    def get_export_data(self, from_date: date, to_date: date) -> List[Dict]:
        if not self.auth.is_configured():
            return []

        payload = {
            "eBRCIssueFromDt": from_date.strftime("%d%m%Y"),
            "eBRCIssueToDt":   to_date.strftime("%d%m%Y"),
            "iecCode":         self.iec_code,
            "sbCumInvoiceNumber": None,
            "sbCumInvoiceDate":   None,
        }

        body, headers = self.auth.build_encrypted_request(payload)
        if body is None:
            logger.info("DGFT fetch skipped — encryption not available")
            return []

        try:
            resp = httpx.post(EBRC_URL, json=body, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            logger.info("DGFT fetchEBRCDetails response: %s", str(data)[:200])
            if isinstance(data, list):
                return data
            return data.get("eBRCRespList", data.get("data", data.get("records", [])))
        except httpx.HTTPStatusError as e:
            logger.error("DGFT HTTP %s: %s", e.response.status_code, e.response.text[:300])
        except Exception as e:
            logger.error("DGFT fetch error: %s", e)
        return []


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

class NIRYATDataLoader:
    """Loads DGFT eBRC records into the warehouse."""

    def __init__(self):
        self.api_client = NIRYATAPIClient()

    def load_recent_exports(self, days_back: int = 30) -> int:
        to_date   = date.today()
        from_date = to_date - timedelta(days=days_back)
        logger.info("Loading DGFT eBRC data %s → %s", from_date, to_date)

        records = self.api_client.get_export_data(from_date, to_date)
        if not records:
            logger.info("No eBRC records returned from DGFT API")
            return 0

        with SessionLocal() as db:
            loaded = 0
            try:
                for record in records:
                    if self._load_export_record(db, record):
                        loaded += 1
                db.commit()
                logger.info("Loaded %d eBRC records from DGFT", loaded)
            except Exception as e:
                db.rollback()
                logger.error("Failed to load DGFT data: %s", e)
                raise
        return loaded

    def _load_export_record(self, db: Session, record: Dict) -> bool:
        # eBRC response fields per spec section 5.6.2
        txn_id = (
            record.get("eBRCNumber") or record.get("eBRCNo") or
            record.get("sb_no") or record.get("sbNo")
        )
        if not txn_id:
            return False

        existing = db.query(FactExportTransaction).filter(
            FactExportTransaction.transaction_id == str(txn_id)
        ).first()
        if existing:
            return False

        exporter  = self._get_or_create_exporter(db, record)
        country   = self._get_country(db, record.get("buyerCountry") or record.get("country_code"))
        hs        = self._get_hs_code(db, record.get("hsCode") or record.get("hs_code"))
        date_key  = self._get_date_key(db, record.get("eBRCDate") or record.get("sbCumInvoiceDate"))
        transport = self._get_transport_mode(db, record.get("modeOfTransport") or record.get("mode_of_transport"))

        try:
            fob = float(record.get("realisedValueFCC") or record.get("fobFCC") or 0)
        except (TypeError, ValueError):
            fob = 0.0

        txn = FactExportTransaction(
            transaction_id=str(txn_id),
            export_date_key=date_key,
            exporter_key=exporter.exporter_key if exporter else None,
            destination_country_key=country.country_key if country else None,
            hs_code_key=hs.hs_code_key if hs else None,
            transport_mode_key=transport.transport_mode_key if transport else None,
            value_usd=fob,
            shipment_status="completed",
            source_system="dgft_ebrc",
            extract_date_key=self._get_date_key(db, date.today()),
        )
        db.add(txn)
        return True

    def _get_or_create_exporter(self, db: Session, record: Dict) -> Optional[DimExporter]:
        iec = record.get("iecCode") or record.get("iec_code") or get_settings().dgft_iec_code
        exp = db.query(DimExporter).filter(DimExporter.iec_code == iec).first()
        if not exp:
            exp = DimExporter(
                iec_code=iec,
                company_name=record.get("exporterName") or record.get("exporter_name") or "Unknown",
                is_active=True,
            )
            db.add(exp)
            db.flush()
        return exp

    def _get_country(self, db: Session, code: Optional[str]) -> Optional[DimCountry]:
        if not code:
            return None
        return db.query(DimCountry).filter(
            (DimCountry.iso_alpha_2 == code) | (DimCountry.iso_alpha_3 == code)
        ).first()

    def _get_hs_code(self, db: Session, code: Optional[str]) -> Optional[DimHsCode]:
        if not code:
            return None
        return db.query(DimHsCode).filter(DimHsCode.hs_code == str(code)[:2]).first()

    def _get_date_key(self, db: Session, date_val) -> Optional[int]:
        if not date_val:
            return None
        if isinstance(date_val, str):
            for fmt in ("%d%m%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    from datetime import datetime
                    date_val = datetime.strptime(date_val, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                return None
        dim = db.query(DimDate).filter(DimDate.full_date == date_val).first()
        return dim.date_key if dim else None

    def _get_transport_mode(self, db: Session, mode: Optional[str]) -> Optional[DimTransportMode]:
        if not mode:
            return None
        code = {"SEA": "SEA", "AIR": "AIR", "RAIL": "RAIL", "ROAD": "ROAD"}.get(
            mode.upper()
        )
        if not code:
            return None
        return db.query(DimTransportMode).filter(
            DimTransportMode.transport_mode_code == code
        ).first()
