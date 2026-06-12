"""HTML sanitizer for LLM-generated content"""

import re
from html.parser import HTMLParser
from typing import Set


class HTMLSanitizer(HTMLParser):
    """Strip dangerous tags and attributes from HTML"""

    DANGEROUS_TAGS: Set[str] = {
        "script", "iframe", "object", "embed", "form", "input",
        "textarea", "select", "option", "meta", "link", "base",
        "head", "frameset", "frame", "applet",
        "style", "title", "noscript", "template", "slot",
    }

    DANGEROUS_ATTR_PATTERNS = [
        re.compile(r"^on\w+", re.IGNORECASE),           # onclick, onerror, etc.
        re.compile(r"^javascript:", re.IGNORECASE),      # javascript: protocol
        re.compile(r"^data:text/html", re.IGNORECASE),   # data URI with HTML
        re.compile(r"^vbscript:", re.IGNORECASE),        # vbscript: protocol
    ]

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []
        self._skip_depth = 0

    def _is_dangerous_attr(self, name: str, value: str | None) -> bool:
        """Check if an attribute is dangerous"""
        check = f"{name}={value or ''}"
        for pattern in self.DANGEROUS_ATTR_PATTERNS:
            if pattern.search(check):
                return True
        return False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag.lower() in self.DANGEROUS_TAGS:
            self._skip_depth += 1
            return

        if self._skip_depth > 0:
            return

        safe_attrs = []
        for name, value in attrs:
            if self._is_dangerous_attr(name, value):
                continue
            safe_attrs.append((name, value))

        attr_str = ""
        for name, value in safe_attrs:
            if value is None:
                attr_str += f" {name}"
            else:
                # Escape quotes in value to prevent attribute injection
                safe_value = value.replace("&", "&amp;").replace('"', "&quot;")
                attr_str += f' {name}="{safe_value}"'

        self.output.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag: str):
        if tag.lower() in self.DANGEROUS_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return

        if self._skip_depth > 0:
            return

        self.output.append(f"</{tag}>")

    def handle_data(self, data: str):
        if self._skip_depth == 0:
            self.output.append(data)

    def handle_entityref(self, name: str):
        if self._skip_depth == 0:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str):
        if self._skip_depth == 0:
            self.output.append(f"&#{name};")

    def get_clean_html(self) -> str:
        return "".join(self.output)


def sanitize_html(raw_html: str) -> str:
    """Sanitize HTML by removing dangerous tags and attributes"""
    if not raw_html:
        return ""
    sanitizer = HTMLSanitizer()
    sanitizer.feed(raw_html)
    return sanitizer.get_clean_html()


def validate_prototype_interactions(html_code: str) -> dict:
    """Validate interactive elements in AI-generated prototype HTML.

    Returns a report with issues found and suggestions.
    """
    if not html_code:
        return {"valid": False, "issues": ["Empty HTML"], "score": 0}

    issues = []
    score = 100

    # Extract all JavaScript from script tags
    scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", html_code, re.IGNORECASE)
    js_code = "\n".join(scripts)

    # Extract all function definitions
    func_pattern = re.compile(r"function\s+(\w+)\s*\(|(\w+)\s*[:=]\s*function\s*\(|(\w+)\s*[:=]\s*\([^)]*\)\s*=>|const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>")
    defined_funcs = set()
    for m in func_pattern.finditer(js_code):
        defined_funcs.update(g for g in m.groups() if g)

    # Extract onclick handlers
    onclick_pattern = re.compile(r'onclick\s*=\s*"([^"]*)"')
    onclick_calls = onclick_pattern.findall(html_code)

    for call in onclick_calls:
        # Extract function name from call like "switchPage('home')" or "openModal()"
        match = re.match(r"(\w+)", call.strip())
        if match:
            func_name = match.group(1)
            if func_name not in defined_funcs and func_name not in {"window", "console", "alert", "confirm", "location"}:
                issues.append(f"onclick calls undefined function '{func_name}'")
                score -= 15

    # Check for buttons without click handlers
    button_pattern = re.compile(r"<button[^>]*>(.*?)</button>", re.IGNORECASE | re.DOTALL)
    buttons = button_pattern.findall(html_code)
    buttons_without_handler = 0
    for btn_html in buttons:
        full_btn = f"<button{btn_html}</button>"
        if not re.search(r'onclick\s*=|@click|v-on:click|ng-click', full_btn, re.IGNORECASE):
            buttons_without_handler += 1
    if buttons_without_handler:
        issues.append(f"{buttons_without_handler} button(s) without click handler")
        score -= min(buttons_without_handler * 5, 20)

    # Check for hash routes without handler
    if re.search(r'href\s*=\s*"#', html_code) and not re.search(r'hashchange|window\.addEventListener\s*\(\s*["\']hashchange', js_code, re.IGNORECASE):
        if not re.search(r'onclick.*location\.hash|onclick.*switchPage', html_code, re.IGNORECASE):
            issues.append("Hash links found but no hashchange routing handler detected")
            score -= 10

    # Check for empty links
    empty_links = len(re.findall(r'<a[^>]*href\s*=\s*"#"[^>]*>', html_code, re.IGNORECASE))
    if empty_links:
        issues.append(f"{empty_links} link(s) with empty href='#'")
        score -= min(empty_links * 3, 15)

    score = max(0, score)

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "score": score,
        "buttons_total": len(buttons),
        "buttons_without_handler": buttons_without_handler,
        "defined_functions": list(defined_funcs),
        "onclick_handlers": len(onclick_calls),
    }
