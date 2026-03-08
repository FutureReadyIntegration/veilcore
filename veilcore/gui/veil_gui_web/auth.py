from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError

router = APIRouter()

# Load secret from file if present, otherwise fallback
try:
    with open("/opt/veil_os/gui/veil_gui_web/.jwt_secret","r") as f:
        JWT_SECRET = f.read().strip()
except Exception:
    JWT_SECRET = "change_this_long_random_secret"

JWT_ALGO = "HS256"
ACCESS_EXPIRE_MINUTES = 60

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_token(data: dict, expires_delta: int = ACCESS_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGO)

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    if payload.username == "veil" and payload.password == "supervisor":
        token = create_token({"sub": payload.username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

def get_current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return {"username": payload.get("sub")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/me")
def me(user = Depends(get_current_user)):
    return user
