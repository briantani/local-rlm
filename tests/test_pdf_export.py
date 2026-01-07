"""
Tests for PDF export functionality.
Phase 17: Canvas & Export Features - PDF Export
"""

from io import BytesIO


def test_weasyprint_import():
    """Test that WeasyPrint is available."""
    import weasyprint  # noqa: F401


def test_markdown_import():
    """Test that markdown library is available."""
    import markdown  # noqa: F401


def test_export_routes_loaded():
    """Test that export routes module loads correctly."""
    from src.web.routes import export

    # Verify it has a router
    assert hasattr(export, 'router')

    # Check available routes
    routes = [route.path for route in export.router.routes]

    # Should have all three export endpoints
    assert any('/markdown' in route for route in routes)
    assert any('/json' in route for route in routes)
    assert any('/pdf' in route for route in routes)


def test_pdf_endpoint_registered():
    """Test that the PDF export endpoint is registered."""
    from src.web.routes import export

    routes = [route.path for route in export.router.routes]
    pdf_routes = [r for r in routes if '/pdf' in r]

    assert len(pdf_routes) == 1
    assert '/api/tasks/{task_id}/export/pdf' in pdf_routes[0]


def test_basic_pdf_generation():
    """Test that WeasyPrint can generate a valid PDF."""
    from weasyprint import HTML

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test PDF</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            h1 { color: blue; }
        </style>
    </head>
    <body>
        <h1>Test PDF Generation</h1>
        <p>This is a test PDF document.</p>
        <code>print("Hello, World!")</code>
    </body>
    </html>
    """

    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)

    pdf_content = pdf_file.getvalue()

    # Verify PDF was generated
    assert len(pdf_content) > 0

    # Verify PDF header
    assert pdf_content.startswith(b'%PDF-')

    # Verify minimum size (should be several KB)
    assert len(pdf_content) > 5000


def test_pdf_with_markdown_content():
    """Test PDF generation with markdown-converted HTML."""
    from weasyprint import HTML
    import markdown

    md_content = """
# Test Document

This is a **bold** statement with *italic* text.

## Code Example

```python
def hello():
    print("Hello, World!")
```

- Item 1
- Item 2
- Item 3
"""

    # Convert markdown to HTML
    html_body = markdown.markdown(md_content, extensions=['fenced_code'])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            code {{ background-color: #f0f0f0; padding: 2px 4px; }}
            pre {{ background-color: #2d2d2d; color: #f0f0f0; padding: 10px; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)

    pdf_content = pdf_file.getvalue()

    # Verify PDF was generated with content
    assert len(pdf_content) > 0
    assert pdf_content.startswith(b'%PDF-')
