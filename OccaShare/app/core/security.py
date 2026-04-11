from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..db import database, models, crud

# Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours. Frontend inactivity JS handles the 15-minute idle timeout.
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int, db: Session):
    import uuid
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    token = jwt.encode({
        "sub": str(user_id), 
        "exp": expire, 
        "type": "refresh",
        "jti": jti
    }, SECRET_KEY, algorithm=ALGORITHM)
    
    db_token = models.RefreshToken(user_id=user_id, token=token, expires_at=expire)
    db.add(db_token)
    db.commit()
    return token

def verify_token(token: str, db: Session):
    """Helper to verify a raw JWT string and return the user."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = db.query(models.User).filter(models.User.email == email).first()
        return user
    except JWTError:
        return None

async def get_current_user(request: Request, db: Session = Depends(database.get_db)):
    """Centralized dependency to get the current user from session cookies."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get token from cookie or Authorization header
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]
    
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_optional(request: Request, db: Session = Depends(database.get_db)) -> Optional[models.User]:
    """Optional version of get_current_user that returns None instead of raising."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None

class RoleChecker:
    """Dependency for role-based access control."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: models.User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return user
