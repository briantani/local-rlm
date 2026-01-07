"""
JavaScript Syntax Validation Tests.

Validates that JavaScript code in templates is syntactically correct.
Uses Node.js to parse and validate JavaScript syntax.
"""
import re
import subprocess
from pathlib import Path

import pytest


class TestJavaScriptSyntax:
    """Tests for JavaScript syntax validation in templates."""

    def extract_javascript(self, template_path: Path) -> list[tuple[str, int]]:
        """Extract JavaScript code blocks from HTML templates.

        Returns:
            List of (javascript_code, line_number) tuples
        """
        content = template_path.read_text()
        js_blocks = []

        # Find <script> blocks (excluding CDN imports)
        script_pattern = r'<script(?![^>]*src=)>(.*?)</script>'
        for match in re.finditer(script_pattern, content, re.DOTALL):
            js_code = match.group(1)
            # Calculate line number
            line_num = content[:match.start()].count('\n') + 1
            js_blocks.append((js_code, line_num))

        return js_blocks

    def validate_javascript_syntax(self, js_code: str, filename: str, line_offset: int = 0) -> tuple[bool, str]:
        """Validate JavaScript syntax using Node.js.

        Args:
            js_code: JavaScript code to validate
            filename: Name of file for error reporting
            line_offset: Line number offset in original file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to run node with syntax check only
            result = subprocess.run(
                ['node', '--check'],
                input=js_code,
                text=True,
                capture_output=True,
                timeout=5
            )

            if result.returncode != 0:
                error_msg = result.stderr
                # Try to adjust line numbers in error messages
                if line_offset > 0:
                    error_msg = f"{filename} (starting at line {line_offset})\n{error_msg}"
                return False, error_msg

            return True, ""

        except FileNotFoundError:
            # Node.js not installed - skip validation
            pytest.skip("Node.js not installed - skipping JavaScript syntax validation")
        except subprocess.TimeoutExpired:
            return False, "JavaScript validation timed out"

    def test_index_page_javascript_syntax(self):
        """Test that index.html has valid JavaScript syntax."""
        template_path = Path("src/web/templates/index.html")

        if not template_path.exists():
            pytest.skip("Template not found")

        js_blocks = self.extract_javascript(template_path)

        for js_code, line_num in js_blocks:
            is_valid, error = self.validate_javascript_syntax(
                js_code,
                template_path.name,
                line_num
            )
            assert is_valid, f"JavaScript syntax error in {template_path.name}:\n{error}"

    def test_base_template_javascript_syntax(self):
        """Test that base.html has valid JavaScript syntax."""
        template_path = Path("src/web/templates/base.html")

        if not template_path.exists():
            pytest.skip("Template not found")

        js_blocks = self.extract_javascript(template_path)

        for js_code, line_num in js_blocks:
            is_valid, error = self.validate_javascript_syntax(
                js_code,
                template_path.name,
                line_num
            )
            assert is_valid, f"JavaScript syntax error in {template_path.name}:\n{error}"

    def test_component_templates_javascript_syntax(self):
        """Test that component templates have valid JavaScript syntax."""
        components_dir = Path("src/web/templates/components")

        if not components_dir.exists():
            pytest.skip("Components directory not found")

        for template_path in components_dir.glob("*.html"):
            js_blocks = self.extract_javascript(template_path)

            for js_code, line_num in js_blocks:
                is_valid, error = self.validate_javascript_syntax(
                    js_code,
                    template_path.name,
                    line_num
                )
                assert is_valid, f"JavaScript syntax error in {template_path.name}:\n{error}"

    def test_all_templates_for_common_syntax_errors(self):
        """Test all templates for common JavaScript syntax errors."""
        templates_dir = Path("src/web/templates")

        if not templates_dir.exists():
            pytest.skip("Templates directory not found")

        errors = []

        for template_path in templates_dir.rglob("*.html"):
            content = template_path.read_text()

            # Check for duplicate async function definitions
            # This catches the specific bug we just fixed where there were two
            # async onConfigChange() functions
            async_functions = re.findall(r'async\s+function\s+(\w+)\s*\([^)]*\)\s*\{', content)
            seen = set()
            for func_name in async_functions:
                if func_name in seen:
                    errors.append(
                        f"{template_path.name}: Duplicate async function definition: {func_name}"
                    )
                seen.add(func_name)

        assert len(errors) == 0, "JavaScript syntax issues found:\n" + "\n".join(errors)
