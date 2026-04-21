from __future__ import annotations

from markitdown import MarkItDown

from ._converter import KatexHtmlConverter

__all__ = [
    "KatexHtmlConverter",
    "__plugin_interface_version__",
    "register_converters",
]

__plugin_interface_version__ = 1

KATEX_HTML_PRIORITY = 9.0


def register_converters(markitdown: MarkItDown, **kwargs: object) -> None:
    """Register converters exposed by this plugin."""
    del kwargs
    markitdown.register_converter(KatexHtmlConverter(), priority=KATEX_HTML_PRIORITY)
