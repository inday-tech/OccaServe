from app.db.database import SessionLocal
from app.db.models import CatererProfile, IdentityVerification, CatererVerification, VerificationDocument
from datetime import datetime

def migrate_pending_caterers():
    db = SessionLocal()
    try:
        pending_caterers = db.query(CatererProfile).filter(
            CatererProfile.verification_status.in_(['Pending', 'Pending Review', 'Requires Revision'])
        ).all()
        
        for caterer in pending_caterers:
            print(f"Migrating caterer {caterer.business_name} (ID: {caterer.id})")
            
            # Check if verification already exists
            existing_verif = db.query(CatererVerification).filter_by(caterer_id=caterer.id).first()
            if existing_verif:
                print("Already has verification record, skipping.")
                continue
                
            # Find IdentityVerification
            iv = db.query(IdentityVerification).filter_by(user_id=caterer.user_id).first()
            
            # Create CatererVerification
            status_map = {
                'Pending': 'PENDING_REVIEW',
                'Pending Review': 'PENDING_REVIEW',
                'Requires Revision': 'RESUBMISSION_REQUIRED'
            }
            new_status = status_map.get(caterer.verification_status, 'PENDING_REVIEW')
            
            new_verif = CatererVerification(
                caterer_id=caterer.id,
                status=new_status,
                submitted_at=datetime.utcnow()
            )
            db.add(new_verif)
            db.flush() # To get new_verif.id
            
            # Add Documents
            if iv and iv.document_url:
                doc_id = VerificationDocument(
                    verification_id=new_verif.id,
                    document_type='GOVERNMENT_ID',
                    secure_file_path=iv.document_url,
                    uploaded_at=iv.created_at or datetime.utcnow()
                )
                db.add(doc_id)
                
            if iv and iv.selfie_url:
                doc_selfie = VerificationDocument(
                    verification_id=new_verif.id,
                    document_type='SELFIE',
                    secure_file_path=iv.selfie_url,
                    uploaded_at=iv.created_at or datetime.utcnow()
                )
                db.add(doc_selfie)
                
            # Business Permit from fields
            permit_url = caterer.permit_url or caterer.mayors_permit_url
            if permit_url:
                doc_permit = VerificationDocument(
                    verification_id=new_verif.id,
                    document_type='BUSINESS_PERMIT',
                    secure_file_path=permit_url,
                    uploaded_at=datetime.utcnow()
                )
                db.add(doc_permit)
                
        db.commit()
        print("Migration complete!")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_pending_caterers()
