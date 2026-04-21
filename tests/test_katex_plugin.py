from __future__ import annotations

from io import BytesIO

from markitdown import MarkItDown, StreamInfo

from markitdown_katex_plugin import KATEX_HTML_PRIORITY, KatexHtmlConverter, register_converters


def test_plain_html_is_not_accepted_by_plugin_converter() -> None:
    converter = KatexHtmlConverter()
    stream = BytesIO(b"<html><body><p>Hello <strong>world</strong></p></body></html>")

    accepted = converter.accepts(
        stream,
        StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert accepted is False
    assert stream.tell() == 0


def test_plugin_preserves_inline_and_display_katex_math() -> None:
    html = """
    <html>
      <body>
        <h1>Document</h1>
        <p>before <span class="katex"><span class="katex-mathml"><math><semantics><mrow><msup><mi>x</mi><mn>2</mn></msup></mrow><annotation encoding="application/x-tex">x^2</annotation></semantics></math></span><span class="katex-html" aria-hidden="true"><span class="base">rendered</span></span></span> after</p>
        <span class="katex-display"><span class="katex"><span class="katex-mathml"><math><semantics><mrow><mi>y</mi></mrow><annotation encoding="application/x-tex">\\int_0^1 y \\, dy</annotation></semantics></math></span><span class="katex-html" aria-hidden="true"><span class="base">rendered</span></span></span></span>
      </body>
    </html>
    """

    result = MarkItDown(enable_plugins=True).convert_stream(
        BytesIO(html.encode("utf-8")),
        stream_info=StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert "# Document" in result.markdown
    assert "before $x^2$ after" in result.markdown
    assert "$$\n\\int_0^1 y \\, dy\n$$" in result.markdown
    assert "rendered" not in result.markdown
    assert "\\int\\_0^1" not in result.markdown


def test_plain_html_still_uses_builtin_html_conversion() -> None:
    html = "<html><body><p>Hello <strong>world</strong></p></body></html>"

    result = MarkItDown(enable_plugins=True).convert_stream(
        BytesIO(html.encode("utf-8")),
        stream_info=StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert result.markdown == "Hello **world**"


def test_register_converters_uses_expected_priority() -> None:
    registered: list[tuple[object, float]] = []

    class DummyMarkItDown:
        def register_converter(self, converter: object, *, priority: float) -> None:
            registered.append((converter, priority))

    register_converters(DummyMarkItDown())

    assert len(registered) == 1
    converter, priority = registered[0]
    assert isinstance(converter, KatexHtmlConverter)
    assert priority == KATEX_HTML_PRIORITY
