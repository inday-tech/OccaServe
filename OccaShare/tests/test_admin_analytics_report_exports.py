import io
import re
import zipfile
from xml.etree import ElementTree

from app.services.audit_report import build_sectioned_report_docx, build_sectioned_report_pdf


REPORT_SECTIONS = [
    ("Summary metrics", ["Metric", "Value"], [["Bookings", "12"]]),
    (
        "Monthly booking trend",
        ["Month", "Bookings"],
        [["Jan 2026", "5"], ["Feb 2026", "7"]],
    ),
]


def test_analytics_word_export_is_valid_and_includes_all_report_sections():
    content = build_sectioned_report_docx(
        "OccaServe Analytics Report",
        "Feb 28, 2026 10:00 AM PHT",
        REPORT_SECTIONS,
    )

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        document_xml = archive.read("word/document.xml")
        ElementTree.fromstring(document_xml)
        document = document_xml.decode("utf-8")
        assert archive.read("word/media/brand_icon.png").startswith(b"\x89PNG")
        assert "word/_rels/document.xml.rels" in archive.namelist()

    assert "OccaServe Analytics Report" in document
    assert "Monthly booking trend" in document
    assert "Jan 2026" in document
    assert "Feb 2026" in document
    assert 'w:orient="landscape"' in document
    assert '<w:tblLayout w:type="fixed"/>' in document
    assert "<w:tcMar>" in document
    assert "F07835" in document


def test_analytics_pdf_export_has_valid_xref_and_includes_all_report_sections():
    content = build_sectioned_report_pdf(
        "OccaServe Analytics Report",
        "Feb 28, 2026 10:00 AM PHT",
        REPORT_SECTIONS,
    )
    xref_offset = int(re.search(rb"startxref\n(\d+)\n%%EOF", content).group(1))

    assert content.startswith(b"%PDF-1.4")
    assert content[xref_offset:xref_offset + 4] == b"xref"
    assert b"/Subtype /Image" in content
    assert b"OCCASERVE" in content
    assert b"Monthly booking trend" in content
    assert b"Jan 2026" in content
    assert b"Feb 2026" in content
