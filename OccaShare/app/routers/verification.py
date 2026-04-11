from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
import base64
import os
import uuid
import time
from typing import Optional, List
from ..db import database, models
from ..core import security as auth
from ..services.verification import verification_service

router = APIRouter(prefix="/api/verify", tags=["verification"])

# This router is deprecated and kept for backward compatibility if needed.
# New KYC logic is in routers/kyc.py
