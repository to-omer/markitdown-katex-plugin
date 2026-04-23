# MarkItDown KaTeX Plugin

`markitdown-katex-plugin` is a [MarkItDown](https://github.com/microsoft/markitdown) plugin for HTML that contains KaTeX or MathJax math.

Its goal is narrow: convert original TeX back into Markdown math instead of letting the default HTML converter flatten rendered math or escape TeX characters such as `_`.

## Supported Input

This plugin supports KaTeX standard `htmlAndMathml` output, where the original TeX is present in:

```html
<annotation encoding="application/x-tex">...</annotation>
```

It also supports rendered MathJax HTML when the original TeX remains in the rendered DOM:

- MathJax v3/v4 CommonHTML nodes with `mjx-math[data-latex]`
- MathJax v2 rendered nodes paired with generated `<script type="math/tex" id="MathJax-Element-...">...</script>`

The plugin does not try to recover math from KaTeX fragments without `application/x-tex` annotations, unrendered MathJax source delimiters, unrendered MathJax script tags, or rendered MathJax output that no longer contains the original TeX source.

## Output

- Inline math becomes `$...$`
- Display math becomes `$$...$$`

## Installation And Verification

Install directly from GitHub and list available MarkItDown plugins:

```bash
uvx --with "markitdown-katex-plugin @ git+https://github.com/to-omer/markitdown-katex-plugin" --from markitdown markitdown --list-plugins
```

Run a conversion with plugins enabled:

```bash
uvx --with "markitdown-katex-plugin @ git+https://github.com/to-omer/markitdown-katex-plugin" --from markitdown markitdown --use-plugins sample.html
```

Use the Python API through `uvx`:

```bash
uvx --with markitdown --with "markitdown-katex-plugin @ git+https://github.com/to-omer/markitdown-katex-plugin" python -c '
from markitdown import MarkItDown

result = MarkItDown(enable_plugins=True).convert("sample.html")
print(result.markdown)
'
```

## Example

Given HTML that contains KaTeX like:

```html
<p>Area: <span class="katex">...</span></p>
<span class="katex-display">...</span>
```

the Markdown output becomes:

```md
Area: $A = \pi r^2$

$$
\int_0^1 x^2 \, dx
$$
```

## Development

Run the test suite:

```bash
uvx --with . --with pytest pytest
```
