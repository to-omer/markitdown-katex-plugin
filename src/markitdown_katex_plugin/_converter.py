from __future__ import annotations

import re
from io import BytesIO
from typing import Any, BinaryIO
from uuid import uuid4

from bs4 import BeautifulSoup, NavigableString, Tag
from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo
from markitdown.converters import HtmlConverter

ACCEPTED_MIME_TYPE_PREFIXES = (
    "text/html",
    "application/xhtml",
)
ACCEPTED_FILE_EXTENSIONS = {
    ".htm",
    ".html",
}
KATEX_TEX_SELECTOR = 'annotation[encoding="application/x-tex"]'
MATHJAX_SCRIPT_TYPE = "math/tex"

MATHJAX_SCRIPT_TYPE_RE = re.compile(
    r"""type\s*=\s*["']math/tex(?:[;"'\s])""",
    re.IGNORECASE,
)


class KatexHtmlConverter(DocumentConverter):
    """Convert KaTeX/MathJax HTML math into Markdown math."""

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        del kwargs

        if not _is_html_stream(stream_info):
            return False

        stream_data = _read_stream(file_stream)
        return _contains_supported_math_markup(stream_data, stream_info)

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        strict = kwargs.pop("strict", False)
        stream_data = _read_stream(file_stream)
        soup = _parse_html(stream_data, stream_info)
        replacements: dict[str, str] = {}

        _replace_katex_nodes(soup, replacements)
        _replace_mathjax_nodes(soup, replacements)

        html_converter = HtmlConverter()
        result = html_converter.convert(
            BytesIO(str(soup).encode("utf-8")),
            StreamInfo(
                mimetype="text/html",
                extension=".html",
                charset="utf-8",
                filename=stream_info.filename,
                local_path=stream_info.local_path,
                url=stream_info.url,
            ),
            strict=strict,
            **kwargs,
        )

        markdown = result.markdown
        for placeholder, tex in replacements.items():
            markdown = markdown.replace(placeholder, tex)

        return DocumentConverterResult(markdown=markdown, title=result.title)


def _is_html_stream(stream_info: StreamInfo) -> bool:
    mimetype = (stream_info.mimetype or "").lower()
    extension = (stream_info.extension or "").lower()

    if extension in ACCEPTED_FILE_EXTENSIONS:
        return True

    return any(mimetype.startswith(prefix) for prefix in ACCEPTED_MIME_TYPE_PREFIXES)


def _read_stream(file_stream: BinaryIO) -> bytes:
    current_position = file_stream.tell()
    try:
        return file_stream.read()
    finally:
        file_stream.seek(current_position)


def _contains_supported_math_markup(stream_data: bytes, stream_info: StreamInfo) -> bool:
    html = _decode_html(stream_data, stream_info)
    return _contains_katex_markup(html) or _contains_mathjax_rendered_markup(html)


def _decode_html(stream_data: bytes, stream_info: StreamInfo) -> str:
    encoding = stream_info.charset or "utf-8"
    return stream_data.decode(encoding, errors="ignore")


def _contains_katex_markup(html: str) -> bool:
    return "application/x-tex" in html and "katex" in html


def _contains_mathjax_rendered_markup(html: str) -> bool:
    lower_html = html.lower()
    if "<mjx-container" in lower_html and "data-latex" in lower_html:
        return True

    return (
        MATHJAX_SCRIPT_TYPE_RE.search(html) is not None
        and "mathjax-element-" in lower_html
        and "mathjax" in lower_html
    )


def _parse_html(stream_data: bytes, stream_info: StreamInfo) -> BeautifulSoup:
    encoding = stream_info.charset or "utf-8"
    return BeautifulSoup(stream_data, "html.parser", from_encoding=encoding)


def _replace_katex_nodes(soup: BeautifulSoup, replacements: dict[str, str]) -> None:
    for element in soup.select(".katex-display"):
        tex = _extract_tex_annotation(element)
        if tex is None:
            continue
        _replace_node_with_math(
            element,
            tex,
            replacements,
            is_display=True,
            kind="KATEXDISPLAY",
        )

    for element in soup.select("span.katex"):
        if element.find_parent(class_="katex-display") is not None:
            continue
        tex = _extract_tex_annotation(element)
        if tex is None:
            continue
        _replace_node_with_math(
            element,
            tex,
            replacements,
            is_display=False,
            kind="KATEXINLINE",
        )


def _extract_tex_annotation(element: Tag) -> str | None:
    annotation = element.select_one(KATEX_TEX_SELECTOR)
    if annotation is None:
        return None

    tex = annotation.get_text()
    return tex if tex else None


def _replace_mathjax_nodes(soup: BeautifulSoup, replacements: dict[str, str]) -> None:
    _replace_mathjax_container_nodes(soup, replacements)
    _replace_mathjax_script_tags(soup, replacements)


def _replace_mathjax_container_nodes(soup: BeautifulSoup, replacements: dict[str, str]) -> None:
    for element in soup.select("mjx-container"):
        math = element.select_one("mjx-math[data-latex]")
        if math is None:
            continue

        tex = math.get("data-latex")
        if not isinstance(tex, str) or not tex:
            continue

        _replace_node_with_math(
            element,
            tex,
            replacements,
            is_display=element.get("display") == "true",
            kind="MATHJAXCONTAINER",
        )


def _replace_mathjax_script_tags(soup: BeautifulSoup, replacements: dict[str, str]) -> None:
    for element in soup.find_all("script"):
        if not isinstance(element, Tag):
            continue

        script_type = str(element.get("type", "")).strip().lower()
        if not script_type.startswith(MATHJAX_SCRIPT_TYPE):
            continue

        rendered_node = _find_rendered_mathjax_node(element)
        if rendered_node is None:
            continue

        tex = element.get_text()
        if not tex:
            continue

        _remove_mathjax_preview(rendered_node)
        _replace_node_with_math(
            rendered_node,
            tex,
            replacements,
            is_display="mode=display" in script_type,
            kind="MATHJAXSCRIPT",
        )
        element.decompose()


def _find_rendered_mathjax_node(script: Tag) -> Tag | None:
    previous = _previous_tag_sibling(script)
    if previous is None:
        return None

    if _has_css_class(previous, "MathJax_Display") or _has_css_class(previous, "MathJax"):
        return previous

    if _has_css_class(previous, "MathJax_Preview"):
        next_tag = _next_tag_sibling(previous)
        if next_tag is not None and _has_css_class(next_tag, "MathJax"):
            return next_tag

    return None


def _remove_mathjax_preview(rendered_node: Tag) -> None:
    preview = _previous_tag_sibling(rendered_node)
    if preview is not None and _has_css_class(preview, "MathJax_Preview"):
        preview.decompose()


def _previous_tag_sibling(element: Tag) -> Tag | None:
    sibling = element.previous_sibling
    while sibling is not None:
        if isinstance(sibling, Tag):
            return sibling
        sibling = sibling.previous_sibling
    return None


def _next_tag_sibling(element: Tag) -> Tag | None:
    sibling = element.next_sibling
    while sibling is not None:
        if isinstance(sibling, Tag):
            return sibling
        sibling = sibling.next_sibling
    return None


def _has_css_class(element: Tag, class_name: str) -> bool:
    classes = element.get("class", [])
    return isinstance(classes, list) and class_name in classes


def _replace_node_with_math(
    element: Tag,
    tex: str,
    replacements: dict[str, str],
    *,
    is_display: bool,
    kind: str,
) -> None:
    placeholder = _store_math_replacement(
        tex,
        replacements,
        is_display=is_display,
        kind=kind,
    )
    if is_display:
        element.replace_with(NavigableString("\n\n" + placeholder + "\n\n"))
    else:
        element.replace_with(NavigableString(placeholder))


def _store_math_replacement(
    tex: str,
    replacements: dict[str, str],
    *,
    is_display: bool,
    kind: str,
) -> str:
    placeholder = _make_placeholder(kind, replacements)
    if is_display:
        replacements[placeholder] = "$$\n" + tex + "\n$$"
    else:
        replacements[placeholder] = "$" + tex + "$"
    return placeholder


def _make_placeholder(kind: str, replacements: dict[str, str]) -> str:
    while True:
        placeholder = f"MARKITDOWNMATH{kind}{uuid4().hex.upper()}TOKEN"
        if placeholder not in replacements:
            return placeholder
