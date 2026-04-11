from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from ..db import crud, schemas, database

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("/api")
async def submit_contact_form_api(
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    phone: str = Form(None),
    db: Session = Depends(database.get_db)
):
    full_message = f"Phone Number: {phone}\n\n{message}" if phone else message
    inquiry_data = schemas.InquiryCreate(name=name, email=email, message=full_message)
    crud.create_inquiry(db, inquiry_data)
    
    # Send notification email to the platform
    try:
        from ..core.email_service import send_notification_email
        from ..core.config import settings
        
        subject = f"New Inquiry: {name}"
        email_body = f"You have received a new inquiry from the contact form.\n\nName: {name}\nEmail: {email}\nPhone: {phone if phone else 'N/A'}\nMessage:\n{message}"
        send_notification_email('occaserveplatform@gmail.com', subject, email_body)
    except Exception as e:
        print(f"Warning: Failed to send contact email notification: {e}")
    
    from fastapi.responses import JSONResponse
    return JSONResponse(content={"status": "success", "message": "Inquiry submitted successfully"})
