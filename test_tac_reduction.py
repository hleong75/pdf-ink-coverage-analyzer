#!/usr/bin/env python3
"""
Test script for TAC Reduction functionality

Creates test PDFs and verifies the TAC reduction feature works correctly.
"""

import sys
import tempfile
import numpy as np
from pathlib import Path

try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

from pdf_ink_analyzer import PDFInkAnalyzer


def create_artificial_high_tac_pdf(output_path: str = None):
    """
    Create a PDF and manually inject CMYK values to simulate high TAC
    """
    if output_path is None:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = f.name
    
    # Create a simple test image with specific RGB values
    # We'll use this as a base and then manually test CMYK reduction
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Rich black areas
    rect1 = fitz.Rect(100, 100, 300, 300)
    page.draw_rect(rect1, color=(0.1, 0.08, 0.06), fill=(0.1, 0.08, 0.06))
    
    # Dark cyan
    rect2 = fitz.Rect(320, 100, 495, 300)
    page.draw_rect(rect2, color=(0, 0.2, 0.2), fill=(0, 0.2, 0.2))
    
    page.insert_text((100, 350), "Artificial High TAC Test", fontsize=16)
    
    doc.save(output_path)
    doc.close()
    
    return output_path


def test_tac_reduction_algorithms():
    """Test the TAC reduction algorithms directly"""
    print("=" * 80)
    print("TAC Reduction Algorithm Test")
    print("=" * 80)
    
    # Create synthetic CMYK data with known high TAC
    height, width = 100, 100
    
    # Create arrays with high TAC (>280%)
    # Rich black: high C, M, Y, and K
    c = np.full((height, width), 80.0)  # 80% Cyan
    m = np.full((height, width), 75.0)  # 75% Magenta
    y = np.full((height, width), 70.0)  # 70% Yellow
    k = np.full((height, width), 60.0)  # 60% Black
    
    # Total TAC = 285%, which exceeds 280%
    tac_before = c + m + y + k
    
    print(f"\nSynthetic CMYK data:")
    print(f"  C: {c[0,0]:.2f}%")
    print(f"  M: {m[0,0]:.2f}%")
    print(f"  Y: {y[0,0]:.2f}%")
    print(f"  K: {k[0,0]:.2f}%")
    print(f"  TAC: {tac_before[0,0]:.2f}%")
    
    # Create analyzer instance with a dummy PDF (just for using the methods)
    # First create a simple dummy PDF file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        dummy_path = f.name
    
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    doc.save(dummy_path)
    doc.close()
    
    analyzer = PDFInkAnalyzer(dummy_path, dpi=150)
    
    # Test GCR reduction
    print("\n" + "-" * 80)
    print("Testing GCR (Gray Component Replacement)")
    print("-" * 80)
    
    c_gcr, m_gcr, y_gcr, k_gcr = analyzer._reduce_tac_gcr(c.copy(), m.copy(), y.copy(), k.copy(), 280.0)
    tac_gcr = c_gcr + m_gcr + y_gcr + k_gcr
    
    print(f"\nAfter GCR reduction to 280%:")
    print(f"  C: {c[0,0]:.2f}% → {c_gcr[0,0]:.2f}% (change: {c_gcr[0,0] - c[0,0]:.2f}%)")
    print(f"  M: {m[0,0]:.2f}% → {m_gcr[0,0]:.2f}% (change: {m_gcr[0,0] - m[0,0]:.2f}%)")
    print(f"  Y: {y[0,0]:.2f}% → {y_gcr[0,0]:.2f}% (change: {y_gcr[0,0] - y[0,0]:.2f}%)")
    print(f"  K: {k[0,0]:.2f}% → {k_gcr[0,0]:.2f}% (change: {k_gcr[0,0] - k[0,0]:.2f}%)")
    print(f"  TAC: {tac_before[0,0]:.2f}% → {tac_gcr[0,0]:.2f}% (reduction: {tac_before[0,0] - tac_gcr[0,0]:.2f}%)")
    
    # Verify GCR reduction
    assert tac_gcr[0,0] <= 280.0, "GCR should reduce TAC to target or below"
    assert c_gcr[0,0] < c[0,0], "GCR should reduce CMY"
    assert k_gcr[0,0] > k[0,0], "GCR should increase K"
    print("✓ GCR reduction working correctly")
    
    # Test UCR reduction
    print("\n" + "-" * 80)
    print("Testing UCR (Under Color Removal)")
    print("-" * 80)
    
    c_ucr, m_ucr, y_ucr, k_ucr = analyzer._reduce_tac_ucr(c.copy(), m.copy(), y.copy(), k.copy(), 280.0)
    tac_ucr = c_ucr + m_ucr + y_ucr + k_ucr
    
    print(f"\nAfter UCR reduction to 280%:")
    print(f"  C: {c[0,0]:.2f}% → {c_ucr[0,0]:.2f}% (change: {c_ucr[0,0] - c[0,0]:.2f}%)")
    print(f"  M: {m[0,0]:.2f}% → {m_ucr[0,0]:.2f}% (change: {m_ucr[0,0] - m[0,0]:.2f}%)")
    print(f"  Y: {y[0,0]:.2f}% → {y_ucr[0,0]:.2f}% (change: {y_ucr[0,0] - y[0,0]:.2f}%)")
    print(f"  K: {k[0,0]:.2f}% → {k_ucr[0,0]:.2f}% (change: {k_ucr[0,0] - k[0,0]:.2f}%)")
    print(f"  TAC: {tac_before[0,0]:.2f}% → {tac_ucr[0,0]:.2f}% (reduction: {tac_before[0,0] - tac_ucr[0,0]:.2f}%)")
    
    # Verify UCR reduction (allow small tolerance for floating point)
    assert tac_ucr[0,0] <= 280.1, f"UCR should reduce TAC to target or below (got {tac_ucr[0,0]:.2f}%)"
    assert c_ucr[0,0] < c[0,0], "UCR should reduce CMY"
    print("✓ UCR reduction working correctly")
    
    # Test with TAC already below target
    print("\n" + "-" * 80)
    print("Testing with TAC already below target")
    print("-" * 80)
    
    c_low = np.full((10, 10), 20.0)
    m_low = np.full((10, 10), 20.0)
    y_low = np.full((10, 10), 20.0)
    k_low = np.full((10, 10), 20.0)
    
    tac_low = c_low + m_low + y_low + k_low
    print(f"  Input TAC: {tac_low[0,0]:.2f}% (below 280% target)")
    
    c_low_gcr, m_low_gcr, y_low_gcr, k_low_gcr = analyzer._reduce_tac_gcr(c_low, m_low, y_low, k_low, 280.0)
    tac_low_gcr = c_low_gcr + m_low_gcr + y_low_gcr + k_low_gcr
    
    print(f"  After GCR: {tac_low_gcr[0,0]:.2f}% (should be unchanged)")
    
    assert np.allclose(tac_low, tac_low_gcr), "TAC below target should remain unchanged"
    print("✓ No reduction applied when TAC is already below target")


def test_cli_interface():
    """Test the CLI interface for TAC reduction"""
    print("\n" + "=" * 80)
    print("CLI Interface Test")
    print("=" * 80)
    
    # Create test PDF
    test_pdf = create_artificial_high_tac_pdf()
    print(f"\nCreated test PDF: {test_pdf}")
    
    # Test help message
    import subprocess
    result = subprocess.run(
        ['python', 'pdf_ink_analyzer.py', '--help'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, "Help should work"
    assert '--reduce-tac' in result.stdout, "Help should mention --reduce-tac"
    assert '--method' in result.stdout, "Help should mention --method"
    print("✓ CLI help message includes TAC reduction options")
    
    # Test basic analysis (should work without errors)
    result = subprocess.run(
        ['python', 'pdf_ink_analyzer.py', test_pdf, '--quiet'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, "Basic analysis should work"
    print("✓ Basic analysis completed successfully")
    
    # Test TAC reduction
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        output_pdf = f.name
    
    result = subprocess.run(
        ['python', 'pdf_ink_analyzer.py', test_pdf, 
         '--reduce-tac', '250', '--output', output_pdf],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, "TAC reduction should work"
    assert Path(output_pdf).exists(), "Output PDF should be created"
    print(f"✓ TAC reduction created output PDF: {output_pdf}")
    
    # Test error handling (missing output parameter)
    result = subprocess.run(
        ['python', 'pdf_ink_analyzer.py', test_pdf, '--reduce-tac', '280'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode != 0, "Should fail without --output"
    print("✓ Error handling works correctly")


def run_all_tests():
    """Run all TAC reduction tests"""
    print("=" * 80)
    print("PDF Ink Coverage Analyzer - TAC Reduction Test Suite")
    print("=" * 80)
    
    try:
        test_tac_reduction_algorithms()
        test_cli_interface()
        
        print("\n" + "=" * 80)
        print("All TAC reduction tests passed! ✓")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    run_all_tests()
