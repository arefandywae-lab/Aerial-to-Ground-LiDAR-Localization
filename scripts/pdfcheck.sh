which pdftotext || (apt list --installed 2>/dev/null | grep -i poppler | head -2)
python3 -c "import fitz; print(\"pymupdf ok\")" 2>&1 | tail -n 1
python3 -c "import pypdf; print(\"pypdf ok\")" 2>&1 | tail -n 1
