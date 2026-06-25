from pathlib import Path

pdf_bytes = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    b"4 0 obj << /Length 310 >>\nstream\n"
    b"BT\n"
    b"/F1 16 Tf\n"
    b"50 750 Td\n"
    b"(Introduction to Machine Learning) Tj\n"
    b"0 -35 Td\n"
    b"/F1 11 Tf\n"
    b"(Machine learning is a subset of artificial intelligence.) Tj\n"
    b"0 -20 Td\n"
    b"(It enables computers to learn from data without explicit programming.) Tj\n"
    b"0 -20 Td\n"
    b"(Deep learning uses neural networks with multiple layers.) Tj\n"
    b"0 -20 Td\n"
    b"(Applications include image recognition and natural language processing.) Tj\n"
    b"ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000284 00000 n \n"
    b"0000000660 00000 n \n"
    b"trailer << /Size 6 /Root 1 0 R >>\n"
    b"startxref\n736\n%%EOF\n"
)

Path("test_sample.pdf").write_bytes(pdf_bytes)
print("test_sample.pdf created")
