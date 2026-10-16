from types import SimpleNamespace

from app.routers.caterer_dashboard import (
    _government_id_files_approved,
    _verification_file_feedback_for_current_paths,
)


def test_file_feedback_ignores_stale_review_status_for_replaced_upload():
    documents = [
        SimpleNamespace(
            id=1,
            document_type="DTI_REGISTRATION",
            secure_file_path="/uploads/old-dti.jpg",
            status="INVALID",
        ),
        SimpleNamespace(
            id=2,
            document_type="DTI_REGISTRATION",
            secure_file_path="/uploads/current-dti.jpg",
            status="PENDING",
        ),
    ]

    feedback = _verification_file_feedback_for_current_paths(
        documents,
        {"DTI_REGISTRATION": "/uploads/current-dti.jpg"},
        [],
    )

    assert feedback == {
        "DTI_REGISTRATION": {
            "status": "PENDING",
            "message": "This file is waiting for admin review.",
        }
    }


def test_file_feedback_keeps_replace_eligible_only_for_current_invalid_file():
    documents = [
        SimpleNamespace(
            id=1,
            document_type="BIR_REGISTRATION",
            secure_file_path="/uploads/current-bir.jpg",
            status="INVALID",
        ),
        SimpleNamespace(
            id=2,
            document_type="GOVERNMENT_ID",
            secure_file_path="/uploads/current-id.jpg",
            status="VALID",
        ),
    ]

    feedback = _verification_file_feedback_for_current_paths(
        documents,
        {
            "BIR_REGISTRATION": "/uploads/current-bir.jpg",
            "GOVERNMENT_ID": "/uploads/current-id.jpg",
        },
        [
            SimpleNamespace(
                action="Requested revision for document: BIR_REGISTRATION",
                reason="BIR registration: Image is blurry or unreadable",
            )
        ],
    )

    assert feedback["BIR_REGISTRATION"]["status"] == "INVALID"
    assert feedback["GOVERNMENT_ID"]["status"] == "VALID"


def test_government_id_is_locked_only_when_both_sides_are_approved():
    assert _government_id_files_approved({
        "GOVERNMENT_ID": {"status": "VALID"},
        "GOVERNMENT_ID_BACK": {"status": "VALID"},
    })
    assert not _government_id_files_approved({
        "GOVERNMENT_ID": {"status": "VALID"},
        "GOVERNMENT_ID_BACK": {"status": "PENDING"},
    })
    assert not _government_id_files_approved({
        "GOVERNMENT_ID": {"status": "INVALID"},
        "GOVERNMENT_ID_BACK": {"status": "VALID"},
    })
    assert not _government_id_files_approved({
        "GOVERNMENT_ID": {"status": "VALID"},
    })
