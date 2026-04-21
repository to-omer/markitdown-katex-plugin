from __future__ import annotations

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


class KatexHtmlConverter(DocumentConverter):
    """Convert KaTeX HTML fragments into Markdown math."""

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
        return _contains_katex_markup(stream_data, stream_info)

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

        for element in soup.select(".katex-display"):
            tex = _extract_tex_annotation(element)
            if tex is None:
                continue
            placeholder = _make_placeholder("BLOCK", replacements)
            replacements[placeholder] = "$$\n" + tex + "\n$$"
            element.replace_with(NavigableString("\n\n" + placeholder + "\n\n"))

        for element in soup.select("span.katex"):
            if element.find_parent(class_="katex-display") is not None:
                continue
            tex = _extract_tex_annotation(element)
            if tex is None:
                continue
            placeholder = _make_placeholder("INLINE", replacements)
            replacements[placeholder] = "$" + tex + "$"
            element.replace_with(NavigableString(placeholder))

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


def _contains_katex_markup(stream_data: bytes, stream_info: StreamInfo) -> bool:
    encoding = stream_info.charset or "utf-8"
    html = stream_data.decode(encoding, errors="ignore")
    return "application/x-tex" in html and "katex" in html


def _parse_html(stream_data: bytes, stream_info: StreamInfo) -> BeautifulSoup:
    encoding = stream_info.charset or "utf-8"
    return BeautifulSoup(stream_data, "html.parser", from_encoding=encoding)


def _extract_tex_annotation(element: Tag) -> str | None:
    annotation = element.select_one(KATEX_TEX_SELECTOR)
    if annotation is None:
        return None

    tex = annotation.get_text()
    return tex if tex else None


def _make_placeholder(kind: str, replacements: dict[str, str]) -> str:
    while True:
        placeholder = f"MARKITDOWNKATEX{kind}{uuid4().hex.upper()}TOKEN"
        if placeholder not in replacements:
            return placeholder
