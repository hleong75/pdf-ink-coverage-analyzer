#!/usr/bin/env python3
"""
Test script for PDF Ink Coverage Analyzer

Creates a simple test PDF with known color patterns and verifies the analyzer works correctly.
"""

import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

from pdf_ink_analyzer import PDFInkAnalyzer


def create_test_pdf(output_path: str = "/tmp/test_document.pdf"):
    """
    Create a simple test PDF with colored rectangles
    
    Args:
        output_path: Path where to save the test PDF
    """
    # Create a new PDF
    doc = fitz.open()
    
    # Page 1: Red rectangle (high magenta and yellow, should show in CMYK)
    page = doc.new_page(width=595, height=842)  # A4 size
    
    # Draw a red rectangle (RGB: 255, 0, 0)
    rect = fitz.Rect(100, 100, 400, 400)
    page.draw_rect(rect, color=(1, 0, 0), fill=(1, 0, 0))
    
    # Add some text
    page.insert_text((100, 450), "Test Page 1: Red Rectangle", fontsize=16)
    
    # Page 2: Blue rectangle (high cyan and magenta)
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(100, 100, 400, 400)
    page.draw_rect(rect, color=(0, 0, 1), fill=(0, 0, 1))
    page.insert_text((100, 450), "Test Page 2: Blue Rectangle", fontsize=16)
    
    # Page 3: Black rectangle (high K)
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(100, 100, 400, 400)
    page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))
    page.insert_text((100, 450), "Test Page 3: Black Rectangle", fontsize=16)
    
    # Save the PDF
    doc.save(output_path)
    doc.close()
    
    print(f"Test PDF created: {output_path}")
    return output_path


def run_test():
    """Run the test"""
    print("=" * 80)
    print("PDF Ink Coverage Analyzer - Test Suite")
    print("=" * 80)
    
    # Create test PDF
    print("\n1. Creating test PDF...")
    test_pdf = create_test_pdf()
    
    # Analyze the test PDF
    print("\n2. Analyzing test PDF...")
    analyzer = PDFInkAnalyzer(test_pdf, dpi=150)
    results = analyzer.analyze()
    
    # Print results
    print("\n3. Analysis Results:")
    analyzer.print_results()
    
    # Export to CSV
    csv_output = "/tmp/test_results.csv"
    print(f"\n4. Exporting to CSV: {csv_output}")
    analyzer.export_to_csv(csv_output)
    
    # Export to JSON
    json_output = "/tmp/test_results.json"
    print(f"\n5. Exporting to JSON: {json_output}")
    analyzer.export_to_json(json_output)
    
    # Verify basic expectations
    print("\n6. Verification:")
    assert len(results) == 3, "Should have 3 pages"
    print("✓ Correct number of pages analyzed")
    
    # Page 1 should have high magenta and yellow (red) - reduced threshold as rectangles don't cover full page
    assert results[0]['magenta_avg'] > 5, "Page 1 should have magenta"
    assert results[0]['yellow_avg'] > 5, "Page 1 should have yellow"
    assert results[0]['cyan_avg'] < 5, "Page 1 should have low cyan"
    print("✓ Page 1 (red) has expected CMYK values")
    
    # Page 2 should have high cyan and magenta (blue)
    assert results[1]['cyan_avg'] > 5, "Page 2 should have cyan"
    assert results[1]['magenta_avg'] > 5, "Page 2 should have magenta"
    assert results[1]['yellow_avg'] < 5, "Page 2 should have low yellow"
    print("✓ Page 2 (blue) has expected CMYK values")
    
    # Page 3 should have high black
    assert results[2]['black_avg'] > 5, "Page 3 should have black"
    assert results[2]['cyan_avg'] < 5, "Page 3 should have low cyan"
    assert results[2]['magenta_avg'] < 5, "Page 3 should have low magenta"
    print("✓ Page 3 (black) has expected CMYK values")
    
    # Check that CSV file was created
    assert Path(csv_output).exists(), "CSV file should exist"
    print(f"✓ CSV file created: {csv_output}")
    
    # Check that JSON file was created
    assert Path(json_output).exists(), "JSON file should exist"
    print(f"✓ JSON file created: {json_output}")
    
    print("\n" + "=" * 80)
    print("All tests passed! ✓")
    print("=" * 80)
    
    print("\nTest files created:")
    print(f"  - PDF: {test_pdf}")
    print(f"  - CSV: {csv_output}")
    print(f"  - JSON: {json_output}")


if __name__ == '__main__':
    try:
        run_test()
    except Exception as e:
        print(f"\nTest failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
