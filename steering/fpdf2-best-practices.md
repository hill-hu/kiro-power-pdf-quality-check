# fpdf2 Best Practices for CJK+English Mixed Content

## Overview

This guide documents known pitfalls and solutions when using fpdf2 to generate PDF from Markdown with Chinese-English mixed content. Each issue includes the problem, root cause, and verified fix.

## Critical Rules

These rules apply to ALL fpdf2 PDF generation with CJK content:

1. **Always `align='L'`** — never use default justify for CJK text
2. **Always `set_x(l_margin)` before `multi_cell()`** — prevents "not enough space" errors
3. **Always calculate row height with `dry_run=True`** — never estimate manually for CJK
4. **Always strip markdown formatting** before rendering
5. **Always strip HTML comments** from source
6. **Always replace emoji** — CJK fonts don't support them
7. **Use Microsoft YaHei (msyh.ttc)** for CJK+English mixed rendering

## Known Pitfalls and Fixes

### 1. CJK+English Mixed Text Has Large Gaps

**Problem:** `multi_cell()` inserts large blank spaces between English words/symbols in CJK text.

**Root cause:** Default alignment is justify (两端对齐). fpdf2 stretches word spacing to fill line width, which looks terrible with mixed scripts.

**Fix:** Always use `align='L'` (left-aligned):

```python
# Correct
pdf.multi_cell(0, 5, text, align='L')

# Wrong — causes huge gaps
pdf.multi_cell(0, 5, text)
```

### 2. Table Row Height Too Small — Text Overlaps

**Problem:** Table text overflows cell boundaries, overlapping with next row.

**Root cause:** Manually estimating row height (e.g., `len(text) / col_width * line_height`) doesn't work for CJK characters which have different widths than Latin characters.

**Fix:** Use fpdf2's built-in calculation:

```python
result = pdf.multi_cell(
    cell_width, line_height, cell_text,
    dry_run=True, output='LINES'
)
actual_lines = len(result)
cell_height = actual_lines * line_height + 4  # 4pt safety margin
```

Take the maximum height across all cells in a row.

### 3. "Not enough horizontal space" Error

**Problem:** `FPDFException` when calling `multi_cell()` after a table or indented element.

**Root cause:** Previous element left the x-position near right margin. `multi_cell(0, ...)` calculates width as `page_width - x - right_margin`, which becomes 0 or negative.

**Fix:** Reset x-position before every text output:

```python
pdf.set_x(pdf.l_margin)
pdf.multi_cell(0, 5, text, align='L')
```

### 4. Markdown Bold/Italic Markers in PDF

**Problem:** `**bold**` and `*italic*` appear as literal text in the PDF.

**Fix:** Strip with regex before rendering:

```python
import re
text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold** → bold
text = re.sub(r'\*(.+?)\*', r'\1', text)        # *italic* → italic
```

### 5. HTML Comments in PDF

**Problem:** `<!-- hidden -->` comment content renders as visible text.

**Fix:** Strip from source before processing:

```python
content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
```


### 6. Emoji Causes Blank Rectangles or Errors

**Problem:** Characters like ✅ 🔥 ⏳ render as blank boxes or cause font errors.

**Root cause:** Microsoft YaHei (msyh.ttc) doesn't include emoji glyphs.

**Fix:** Replace emoji with text equivalents before rendering:

```python
EMOJI_MAP = {
    '✅': '[OK]', '❌': '[X]', '⚠️': '[!]',
    '🔴': '[X]', '🟡': '[~]', '🟢': '[OK]',
    '⏳': '[...]', '🔥': '[!]', '📌': '[*]',
    '💡': '[i]', '🚀': '[>]', '📋': '[-]',
}

def replace_emoji(text):
    for emoji, replacement in EMOJI_MAP.items():
        text = text.replace(emoji, replacement)
    return text
```

### 7. Table Columns Too Narrow — Text Truncated

**Problem:** Wide tables with many columns have text cut off at cell boundaries.

**Fix:** Use dynamic column width + landscape orientation for wide tables:

```python
# Landscape A4
pdf = FPDF(orientation='L', unit='pt', format='A4')

# Dynamic column width based on content
max_widths = []
for col_idx in range(num_cols):
    col_texts = [row[col_idx] for row in all_rows]
    max_char = max(len(t) for t in col_texts)
    max_widths.append(max_char)

total = sum(max_widths)
available = pdf.w - pdf.l_margin - pdf.r_margin
col_widths = [(w / total) * available for w in max_widths]
```

Font size guide:
- ≤5 columns: 8.5pt
- 5-7 columns: 7.5pt
- >7 columns: 6.5-7pt

### 8. Deprecated fpdf2 API Warnings

**Problem:** `DeprecationWarning` about `uni=True` or `ln` parameter.

**Fix (fpdf2 v2.5.1+):**

```python
# Font — don't use uni=True
pdf.add_font('yahei', '', 'C:/Windows/Fonts/msyh.ttc')  # no uni param

# Line break — don't use ln=True
pdf.multi_cell(0, 5, text, align='L', new_x='LMARGIN', new_y='NEXT')

# Same line next cell — don't use ln=0
pdf.cell(w, h, text, new_x='RIGHT', new_y='TOP')
```

## Font Configuration

### Recommended Setup

```python
from fpdf import FPDF

pdf = FPDF(orientation='P', unit='pt', format='A4')

# Microsoft YaHei — supports CJK + Latin
pdf.add_font('yahei', '', 'C:/Windows/Fonts/msyh.ttc')
pdf.add_font('yahei', 'B', 'C:/Windows/Fonts/msyhbd.ttc')

pdf.set_font('yahei', '', 10)
```

### macOS/Linux Alternative

```python
# macOS — use PingFang SC
pdf.add_font('pingfang', '', '/System/Library/Fonts/PingFang.ttc')

# Linux — use Noto Sans CJK
pdf.add_font('noto', '', '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc')
```

## Page Layout Reference

### Portrait A4 (default)
- Page: 595 × 842 pt
- Margins: ~28pt each side (default)
- Content width: ~539pt

### Landscape A4
- Page: 842 × 595 pt
- Margins: ~28pt each side
- Content width: ~786pt

Use landscape for tables with >5 columns or total content width >500pt.

## Complete Example: Safe PDF Generation

```python
from fpdf import FPDF
import re, os

def clean_text(text):
    """Remove markdown formatting and emoji."""
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Add your emoji replacements here
    return text

pdf = FPDF(orientation='P', unit='pt', format='A4')
pdf.add_font('yahei', '', 'C:/Windows/Fonts/msyh.ttc')
pdf.add_page()
pdf.set_font('yahei', '', 10)

text = clean_text(source_text)
pdf.set_x(pdf.l_margin)
pdf.multi_cell(0, 14, text, align='L', new_x='LMARGIN', new_y='NEXT')

pdf.output('output.pdf')
```
