"""
Guardian - The Veil Authentication Gateway
==========================================
P0 Security Organ: "I stand between chaos and those I protect."

Guardian provides:
- JWT-based authentication
- Password hashing with bcrypt
- Token generation and validation
- User management
- Brute-force protection
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import base64
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from .models import User, Token, LoginResponse, Role, Session


# ============================================================================
# Configuration
# ============================================================================

class GuardianConfig:
    """Guardian configuration."""
    # JWT Settings
    SECRET_KEY: str = secrets.token_hex(32)  # Generate on first run, persist to file
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Settings
    MIN_PASSWORD_LENGTH: int = 12
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_DIGIT: bool = True
    REQUIRE_SPECIAL: bool = True
    
    # Brute Force Protection
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    
    # Paths
    DATA_DIR: Path = Path("/var/lib/veil/security")
    USERS_FILE: Path = DATA_DIR / "users.json"
    SECRET_FILE: Path = DATA_DIR / "guardian.key"


# ============================================================================
# Password Hashing (bcrypt-compatible using PBKDF2)
# ============================================================================

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """
    Hash a password using PBKDF2-SHA256.
    Returns: salt$hash (both base64 encoded)
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    # Use PBKDF2 with 100,000 iterations
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000,
        dklen=32
    )
    
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    hash_b64 = base64.b64encode(dk).decode('utf-8')
    
    return f"{salt_b64}${hash_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        parts = stored_hash.split('$')
        if len(parts) != 2:
            return False
        
        salt_b64, expected_hash_b64 = parts
        salt = base64.b64decode(salt_b64)
        expected_hash = base64.b64decode(expected_hash_b64)
        
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000,
            dklen=32
        )
        
        return hmac.compare_digest(dk, expected_hash)
    except Exception:
        return False


def validate_password_strength(password: str, config: GuardianConfig = None) -> Tuple[bool, List[str]]:
    """
    Validate password meets security requirements.
    Returns: (is_valid, list_of_errors)
    """
    if config is None:
        config = GuardianConfig()
    
    errors = []
    
    if len(password) < config.MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters")
    
    if config.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if config.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if config.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    if config.REQUIRE_SPECIAL:
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        if not any(c in special_chars for c in password):
            errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors


# ============================================================================
# JWT Token Handling
# ============================================================================

def _base64url_encode(data: bytes) -> str:
    """Base64 URL-safe encode."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data: str) -> bytes:
    """Base64 URL-safe decode."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def create_jwt(payload: Dict[str, Any], secret: str, expires_delta: timedelta = None) -> str:
    """
    Create a JWT token.
    Simple HS256 implementation without external dependencies.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    
    # Add expiration
    now = datetime.utcnow()
    if expires_delta:
        exp = now + expires_delta
    else:
        exp = now + timedelta(hours=1)
    
    payload = {**payload, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    
    # Encode header and payload
    header_b64 = _base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload).encode('utf-8'))
    
    # Create signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_b64 = _base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_jwt(token: str, secret: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Decode and verify a JWT token.
    Returns: (payload, error_message)
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None, "Invalid token format"
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        actual_signature = _base64url_decode(signature_b64)
        
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None, "Invalid signature"
        
        # Decode payload
        payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            return None, "Token expired"
        
        return payload, None
    
    except Exception as e:
        return None, f"Token decode error: {str(e)}"


# ============================================================================
# Guardian Class
# ============================================================================

class Guardian:
    """
    The Veil Authentication Gateway.
    
    Guardian is the P0 security organ that handles all authentication
    for The Veil. It manages users, validates credentials, issues tokens,
    and protects against brute-force attacks.
    """
    
    def __init__(self, config: GuardianConfig = None):
        self.config = config or GuardianConfig()
        self._users: Dict[str, User] = {}
        self._lockouts: Dict[str, datetime] = {}  # username -> lockout_until
        self._init_storage()
        self._load_users()
    
    def _init_storage(self):
        """Initialize storage directories and files."""
        self.config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load or generate secret key
        if self.config.SECRET_FILE.exists():
            self.config.SECRET_KEY = self.config.SECRET_FILE.read_text().strip()
        else:
            self.config.SECRET_KEY = secrets.token_hex(32)
            self.config.SECRET_FILE.write_text(self.config.SECRET_KEY)
            self.config.SECRET_FILE.chmod(0o600)
        
        # Initialize users file
        if not self.config.USERS_FILE.exists():
            self._save_users()
    
    def _load_users(self):
        """Load users from storage."""
        try:
            if self.config.USERS_FILE.exists():
                data = json.loads(self.config.USERS_FILE.read_text())
                for user_data in data.get("users", []):
                    user = User.from_dict(user_data)
                    self._users[user.username] = user
        except Exception:
            self._users = {}
        
        # Ensure default admin exists
        if "admin" not in self._users:
            self.create_user(
                username="admin",
                password="VeilAdmin2024!",  # CHANGE THIS!
                role=Role.ADMIN,
                full_name="Veil Administrator"
            )
    
    def _save_users(self):
        """Save users to storage."""
        data = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "users": [
                {
                    **u.to_dict(),
                    "password_hash": u.password_hash,
                    "updated_at": u.updated_at.isoformat() if u.updated_at else None,
                    "is_locked": u.is_locked,
                    "failed_attempts": u.failed_attempts,
                    "mfa_secret": u.mfa_secret,
                }
                for u in self._users.values()
            ]
        }
        
        # Atomic write
        tmp_file = self.config.USERS_FILE.with_suffix('.tmp')
        tmp_file.write_text(json.dumps(data, indent=2))
        tmp_file.rename(self.config.USERS_FILE)
        self.config.USERS_FILE.chmod(0o600)
    
    def _is_locked_out(self, username: str) -> bool:
        """Check if user is currently locked out."""
        if username in self._lockouts:
            if datetime.utcnow() < self._lockouts[username]:
                return True
            else:
                del self._lockouts[username]
        return False
    
    def _record_failed_attempt(self, username: str):
        """Record a failed login attempt."""
        if username in self._users:
            user = self._users[username]
            user.failed_attempts += 1
            
            if user.failed_attempts >= self.config.MAX_FAILED_ATTEMPTS:
                user.is_locked = True
                self._lockouts[username] = datetime.utcnow() + timedelta(
                    minutes=self.config.LOCKOUT_DURATION_MINUTES
                )
            
            self._save_users()
    
    def _clear_failed_attempts(self, username: str):
        """Clear failed attempts after successful login."""
        if username in self._users:
            self._users[username].failed_attempts = 0
            self._users[username].is_locked = False
            if username in self._lockouts:
                del self._lockouts[username]
            self._save_users()
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def create_user(
        self,
        username: str,
        password: str,
        role: Role,
        email: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Create a new user.
        Returns: (user, error_message)
        """
        # Check if username exists
        if username in self._users:
            return None, "Username already exists"
        
        # Validate password
        is_valid, errors = validate_password_strength(password, self.config)
        if not is_valid:
            return None, "; ".join(errors)
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=hash_password(password),
            role=role,
            email=email,
            full_name=full_name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self._users[username] = user
        self._save_users()
        
        return user, None
    
    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> LoginResponse:
        """
        Authenticate a user and return tokens.
        """
        # Check lockout
        if self._is_locked_out(username):
            return LoginResponse(
                success=False,
                message=f"Account locked. Try again in {self.config.LOCKOUT_DURATION_MINUTES} minutes."
            )
        
        # Check user exists
        user = self._users.get(username)
        if not user:
            return LoginResponse(success=False, message="Invalid credentials")
        
        # Check if active
        if not user.is_active:
            return LoginResponse(success=False, message="Account is disabled")
        
        # Verify password
        if not verify_password(password, user.password_hash):
            self._record_failed_attempt(username)
            remaining = self.config.MAX_FAILED_ATTEMPTS - user.failed_attempts
            return LoginResponse(
                success=False,
                message=f"Invalid credentials. {remaining} attempts remaining."
            )
        
        # Check MFA if enabled
        if user.mfa_enabled:
            return LoginResponse(
                success=False,
                message="MFA required",
                requires_mfa=True
            )
        
        # Success - clear failed attempts and generate tokens
        self._clear_failed_attempts(username)
        user.last_login = datetime.utcnow()
        self._save_users()
        
        # Generate tokens
        access_token = self._generate_access_token(user)
        refresh_token = self._generate_refresh_token(user)
        
        return LoginResponse(
            success=True,
            message="Authentication successful",
            token=Token(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            ),
            user=user.to_dict()
        )
    
    def _generate_access_token(self, user: User) -> str:
        """Generate an access token for a user."""
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "type": "access"
        }
        return create_jwt(
            payload,
            self.config.SECRET_KEY,
            timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    
    def _generate_refresh_token(self, user: User) -> str:
        """Generate a refresh token for a user."""
        payload = {
            "sub": user.id,
            "username": user.username,
            "type": "refresh",
            "jti": str(uuid.uuid4())  # Unique token ID
        }
        return create_jwt(
            payload,
            self.config.SECRET_KEY,
            timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    
    def verify_token(self, token: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Verify an access token and return the user.
        Returns: (user, error_message)
        """
        payload, error = decode_jwt(token, self.config.SECRET_KEY)
        
        if error:
            return None, error
        
        if payload.get("type") != "access":
            return None, "Invalid token type"
        
        username = payload.get("username")
        user = self._users.get(username)
        
        if not user:
            return None, "User not found"
        
        if not user.is_active:
            return None, "Account is disabled"
        
        return user, None
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[Optional[Token], Optional[str]]:
        """
        Use a refresh token to get a new access token.
        Returns: (token, error_message)
        """
        payload, error = decode_jwt(refresh_token, self.config.SECRET_KEY)
        
        if error:
            return None, error
        
        if payload.get("type") != "refresh":
            return None, "Invalid token type"
        
        username = payload.get("username")
        user = self._users.get(username)
        
        if not user or not user.is_active:
            return None, "User not found or disabled"
        
        access_token = self._generate_access_token(user)
        
        return Token(
            access_token=access_token,
            expires_in=self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ), None
    
    def change_password(
        self,
        username: str,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Change a user's password.
        Returns: (success, message)
        """
        user = self._users.get(username)
        if not user:
            return False, "User not found"
        
        if not verify_password(old_password, user.password_hash):
            return False, "Current password is incorrect"
        
        is_valid, errors = validate_password_strength(new_password, self.config)
        if not is_valid:
            return False, "; ".join(errors)
        
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        self._save_users()
        
        return True, "Password changed successfully"
    
    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self._users.get(username)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        for user in self._users.values():
            if user.id == user_id:
                return user
        return None
    
    def list_users(self) -> List[User]:
        """List all users."""
        return list(self._users.values())
    
    def update_user(
        self,
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[Role] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """Update user details."""
        user = self._users.get(username)
        if not user:
            return None, "User not found"
        
        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        
        user.updated_at = datetime.utcnow()
        self._save_users()
        
        return user, None
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Delete a user."""
        if username == "admin":
            return False, "Cannot delete admin user"
        
        if username not in self._users:
            return False, "User not found"
        
        del self._users[username]
        self._save_users()
        
        return True, "User deleted"


# ============================================================================
# Singleton Instance
# ============================================================================

_guardian: Optional[Guardian] = None


def get_guardian() -> Guardian:
    """Get the Guardian singleton instance."""
    global _guardian
    if _guardian is None:
        _guardian = Guardian()
    return _guardian
