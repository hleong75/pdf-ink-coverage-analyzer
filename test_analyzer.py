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

from pdf_ink_analyzer import PDFInkAnalyzer, PrinterProfile


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
    
    # Test basic analysis (without printer profile)
    print("\n2. Testing basic analysis (without printer profile)...")
    analyzer = PDFInkAnalyzer(test_pdf, dpi=150)
    results = analyzer.analyze()
    
    # Print results
    print("\n3. Basic Analysis Results:")
    analyzer.print_results()
    
    # Verify basic expectations
    print("\n4. Verification of basic analysis:")
    assert len(results) == 3, "Should have 3 pages"
    print("✓ Correct number of pages analyzed")
    
    # Page 1 should have high magenta and yellow (red)
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
    
    # Test with printer profile
    print("\n5. Testing with printer profile (inkjet_standard)...")
    profile = PrinterProfile('inkjet_standard')
    analyzer_with_profile = PDFInkAnalyzer(test_pdf, dpi=150, printer_profile=profile)
    results_with_profile = analyzer_with_profile.analyze()
    
    print("\n6. Analysis with Printer Profile:")
    analyzer_with_profile.print_results()
    
    # Verify ink volume calculations
    print("\n7. Verification of ink volume calculations:")
    assert 'ink_total_ml' in results_with_profile[0], "Results should include ink volume"
    print("✓ Ink volume data present in results")
    
    # Check that ink volumes are positive for pages with color
    assert results_with_profile[0]['ink_magenta_ml'] > 0, "Page 1 should have magenta ink"
    assert results_with_profile[0]['ink_yellow_ml'] > 0, "Page 1 should have yellow ink"
    assert results_with_profile[1]['ink_cyan_ml'] > 0, "Page 2 should have cyan ink"
    assert results_with_profile[2]['ink_black_ml'] > 0, "Page 3 should have black ink"
    print("✓ Ink volumes calculated correctly for colored pages")
    
    # Test multiple copies
    print("\n8. Testing summary with multiple copies (50 copies)...")
    summary = analyzer_with_profile.get_summary(copies=50)
    assert summary['copies'] == 50, "Summary should reflect 50 copies"
    assert 'ink_total_ml_all' in summary, "Summary should include total ink volume"
    assert summary['ink_total_ml_all'] > 0, "Total ink volume should be positive"
    print(f"✓ Total ink for 50 copies: {summary['ink_total_ml_all']} mL")
    
    # Export to CSV
    csv_output = "/tmp/test_results.csv"
    print(f"\n9. Exporting to CSV: {csv_output}")
    analyzer_with_profile.export_to_csv(csv_output)
    
    # Export to JSON
    json_output = "/tmp/test_results.json"
    print(f"\n10. Exporting to JSON: {json_output}")
    analyzer_with_profile.export_to_json(json_output, copies=25)
    
    # Check that CSV file was created
    assert Path(csv_output).exists(), "CSV file should exist"
    print(f"✓ CSV file created: {csv_output}")
    
    # Check that JSON file was created
    assert Path(json_output).exists(), "JSON file should exist"
    print(f"✓ JSON file created: {json_output}")
    
    # Test different printer profiles
    print("\n11. Testing different printer profiles...")
    for profile_name in ['inkjet_photo', 'inkjet_office', 'laser']:
        profile = PrinterProfile(profile_name)
        analyzer_test = PDFInkAnalyzer(test_pdf, dpi=150, printer_profile=profile)
        results_test = analyzer_test.analyze()
        assert 'ink_total_ml' in results_test[0], f"Profile {profile_name} should calculate ink"
        print(f"✓ Profile '{profile_name}' works correctly")
    
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
