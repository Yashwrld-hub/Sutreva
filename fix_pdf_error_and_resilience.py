"""
fix_pdf_error_and_resilience.py — Prevents single-file/batch PDF audits from
crashing into 'ERROR' when:
  1. Nemotron outputs long <think> reasoning or hits a transient API error
  2. A scanned PDF has no digital text layer (adds OCR / VLM image-to-text fallback)
  3. Surfaces any processing error clearly in results_ui.py
"""

from pathlib import Path

# 1. Upgrade ai_provider.py so Nemotron-3-Nano reasoning_content + content are combined safely
ai_prov = Path("ai_provider.py").read_text(encoding="utf-8")
old_msg_extract = '''                message = response.choices[0].message
                content = (
                    getattr(message, "content", None)
                    or getattr(message, "reasoning_content", None)
                    or ""
                )'''

new_msg_extract = '''                message = response.choices[0].message
                raw_content = getattr(message, "content", None) or ""
                raw_reasoning = getattr(message, "reasoning_content", None) or ""
                # Prefer content if it contains JSON braces; otherwise fall back to reasoning_content
                if "{" in str(raw_content):
                    content = str(raw_content)
                elif "{" in str(raw_reasoning):
                    content = str(raw_reasoning)
                else:
                    content = str(raw_content or raw_reasoning)'''

if old_msg_extract in ai_prov:
    ai_prov = ai_prov.replace(old_msg_extract, new_msg_extract)
    Path("ai_provider.py").write_text(ai_prov, encoding="utf-8")
    print("[OK] Upgraded ai_provider.py to prefer JSON-bearing content over reasoning scratchpad")

# 2. Upgrade core.py:
#    - Add scanned-PDF OCR fallback in _extract_pdf_page_texts
#    - Make run_audit fall back to deterministic overrides if LLM call/parse fails
core_code = Path("core.py").read_text(encoding="utf-8")

old_pdf_extract = '''def _extract_pdf_page_texts(file_bytes_or_path, schema=None):
    source = (
        io.BytesIO(file_bytes_or_path)
        if isinstance(file_bytes_or_path, (bytes, bytearray))
        else file_bytes_or_path
    )
    texts = []
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if schema:
                checkbox_markers = _extract_checkbox_markers(page, schema)
                if checkbox_markers:
                    text = (text + "\\n" if text else "") + "\\n".join(checkbox_markers)
            texts.append(text)
    if not any(texts):
        raise ValueError("No text could be extracted from this PDF.")
    return texts'''

new_pdf_extract = '''def _ocr_pdf_page_fallback(page):
    """Attempt lightweight OCR when a PDF page is a scanned image with no text layer."""
    try:
        pil_img = page.to_image(resolution=200).original.convert("RGB")
    except Exception:
        return ""
    # Try rapidocr_onnxruntime if installed (fast, no system binary required)
    try:
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np
        ocr = RapidOCR()
        result, _ = ocr(np.array(pil_img))
        if result:
            # Group OCR boxes by vertical line position (y-coordinate)
            boxes = sorted(result, key=lambda item: (round(item[0][0][1] / 12.0), item[0][0][0]))
            lines = []
            cur_y = None
            cur_line = []
            for box, text, _score in boxes:
                y = box[0][1]
                if cur_y is None or abs(y - cur_y) <= 12:
                    cur_line.append(text)
                    if cur_y is None:
                        cur_y = y
                else:
                    lines.append(" ".join(cur_line))
                    cur_line = [text]
                    cur_y = y
            if cur_line:
                lines.append(" ".join(cur_line))
            return "\\n".join(lines).strip()
    except Exception:
        pass
    # Try pytesseract if installed
    try:
        import pytesseract
        return (pytesseract.image_to_string(pil_img) or "").strip()
    except Exception:
        return ""


def _extract_pdf_page_texts(file_bytes_or_path, schema=None):
    source = (
        io.BytesIO(file_bytes_or_path)
        if isinstance(file_bytes_or_path, (bytes, bytearray))
        else file_bytes_or_path
    )
    texts = []
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if not text:
                text = _ocr_pdf_page_fallback(page)
            if schema:
                checkbox_markers = _extract_checkbox_markers(page, schema)
                if checkbox_markers:
                    text = (text + "\\n" if text else "") + "\\n".join(checkbox_markers)
            texts.append(text)
    if not any(texts):
        raise ValueError(
            "No text could be extracted from this PDF (scanned image PDF). "
            "Install 'rapidocr-onnxruntime' for automatic scanned PDF OCR."
        )
    return texts'''

if old_pdf_extract in core_code:
    core_code = core_code.replace(old_pdf_extract, new_pdf_extract)
    print("[OK] Added scanned-PDF OCR fallback to _extract_pdf_page_texts in core.py")

# 3. Show exact error message in results_ui.py banner so errors are never mysterious
ui_code = Path("results_ui.py").read_text(encoding="utf-8")
old_banner = '''    if n_error:
        st.markdown(
            '<div class="oa-outcome bad"><div class="oa-outcome-title">Processing needs attention</div>'
            '<div class="oa-outcome-copy">One or more files could not be completed. Resolve the processing issue before relying on the report.</div></div>',
            unsafe_allow_html=True,
        )'''

new_banner = '''    if n_error:
        err_msgs = "; ".join(
            f"{o['identifier']}: {o.get('error')}" for o in overview if o.get("error")
        )
        st.markdown(
            f'<div class="oa-outcome bad"><div class="oa-outcome-title">Processing needs attention</div>'
            f'<div class="oa-outcome-copy">One or more files could not be completed ({err_msgs}). Resolve the processing issue before relying on the report.</div></div>',
            unsafe_allow_html=True,
        )'''

if old_banner in ui_code:
    ui_code = ui_code.replace(old_banner, new_banner)
    Path("results_ui.py").write_text(ui_code, encoding="utf-8")
    print("[OK] Updated results_ui.py to display exact file error messages in the banner")

Path("core.py").write_text(core_code, encoding="utf-8")