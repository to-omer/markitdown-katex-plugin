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


def test_html_with_plain_dollars_is_not_accepted_without_mathjax_marker() -> None:
    converter = KatexHtmlConverter()
    stream = BytesIO(b"<html><body><p>The cost is $2 and then $3.</p></body></html>")

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


def test_mathjax_source_delimiters_are_out_of_scope() -> None:
    converter = KatexHtmlConverter()
    html = r"""
    <html>
      <head>
        <script>
          window.MathJax = { tex: { inlineMath: [['$', '$'], ['\\(', '\\)']] } };
        </script>
      </head>
      <body>
        <h1>MathJax</h1>
        <p>inline $a_i$ and \(b_i\) are protected.</p>
        <p>\[\sum_{i=1}^n a_i\]</p>
        <p>$$\int_0^1 x^2 \, dx$$</p>
        <p>\begin{align}x_i &= y_i\\z_i &= w_i\end{align}</p>
      </body>
    </html>
    """
    stream = BytesIO(html.encode("utf-8"))

    accepted = converter.accepts(
        stream,
        StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert accepted is False
    assert stream.tell() == 0


def test_plugin_preserves_mathjax_container_latex_attributes() -> None:
    html = r"""
    <html>
      <body>
        <p>inline <mjx-container class="MathJax" jax="CHTML"><mjx-math data-latex="x_i"><mjx-mi>x</mjx-mi></mjx-math></mjx-container> value</p>
        <mjx-container class="MathJax" jax="CHTML" display="true"><mjx-math data-latex="\int_0^1 x \, dx"><mjx-mi>x</mjx-mi></mjx-math></mjx-container>
      </body>
    </html>
    """

    result = MarkItDown(enable_plugins=True).convert_stream(
        BytesIO(html.encode("utf-8")),
        stream_info=StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert "inline $x_i$ value" in " ".join(result.markdown.split())
    assert "$$\n\\int_0^1 x \\, dx\n$$" in result.markdown
    assert "x\\_i" not in result.markdown
    assert "<mjx" not in result.markdown


def test_plugin_preserves_rendered_mathjax_v2_script_tags() -> None:
    html = r"""
    <html>
      <body>
        <p>
          inline
          <span class="MathJax_Preview"></span>
          <span class="MathJax" id="MathJax-Element-1-Frame"><span class="math">rendered inline</span></span>
          <script type="math/tex" id="MathJax-Element-1">x_i</script>
          value
        </p>
        <div class="MathJax_Display" id="MathJax-Element-2-Frame"><span class="MathJax">rendered display</span></div>
        <script type="math/tex; mode=display" id="MathJax-Element-2">\int_0^1 x \, dx</script>
      </body>
    </html>
    """

    result = MarkItDown(enable_plugins=True).convert_stream(
        BytesIO(html.encode("utf-8")),
        stream_info=StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert "inline $x_i$ value" in " ".join(result.markdown.split())
    assert "$$\n\\int_0^1 x \\, dx\n$$" in result.markdown
    assert "rendered inline" not in result.markdown
    assert "rendered display" not in result.markdown
    assert "x\\_i" not in result.markdown


def test_unrendered_mathjax_script_tags_are_out_of_scope() -> None:
    converter = KatexHtmlConverter()
    html = r"""
    <html>
      <body>
        <p>inline <script type="math/tex">x_i</script> value</p>
        <script type="math/tex; mode=display">\int_0^1 x \, dx</script>
      </body>
    </html>
    """
    stream = BytesIO(html.encode("utf-8"))

    accepted = converter.accepts(
        stream,
        StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert accepted is False
    assert stream.tell() == 0


def test_rendered_mathjax_without_source_is_not_accepted() -> None:
    converter = KatexHtmlConverter()
    html = """
    <html>
      <body>
        <mjx-container class="MathJax" jax="CHTML">
          <mjx-math><mjx-msub><mjx-mi>x</mjx-mi><mjx-script><mjx-mi>i</mjx-mi></mjx-script></mjx-msub></mjx-math>
        </mjx-container>
      </body>
    </html>
    """
    stream = BytesIO(html.encode("utf-8"))

    accepted = converter.accepts(
        stream,
        StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
    )

    assert accepted is False
    assert stream.tell() == 0


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
