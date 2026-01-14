import os
if not os.getenv("RLM_RUN_INTEGRATION"):
    import pytest
    pytest.skip("Integration web tests disabled; set RLM_RUN_INTEGRATION=1 to run", allow_module_level=True)

from io import BytesIO


def test_weasyprint_import():
    import weasyprint  # noqa: F401


def test_markdown_import():
    import markdown  # noqa: F401


def test_basic_pdf_generation():
    from weasyprint import HTML
    html_content = "<html><body><h1>PDF</h1></body></html>"
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    pdf_content = pdf_file.getvalue()
    assert len(pdf_content) > 0
    assert pdf_content.startswith(b'%PDF-')
