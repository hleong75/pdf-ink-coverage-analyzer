#!/usr/bin/env python3
"""
Demonstration of the real ink consumption calculation improvement.
This script shows how the new pixel-level calculation with minimum 
printable threshold provides more accurate ink estimates.
"""

import fitz
import sys
from pathlib import Path
from pdf_ink_analyzer import PDFInkAnalyzer, PrinterProfile


def create_demonstration_pdf():
    """Create a PDF that demonstrates the threshold effect"""
    doc = fitz.open()
    
    # Page 1: Document with very light background (common in scanned documents)
    page = doc.new_page(width=595, height=842)  # A4
    
    # Very light gray background (0.5% density - below 1% threshold)
    # This simulates paper texture or very faint watermarks
    LIGHT_GRAY_COLOR = (0.995, 0.995, 0.995)
    bg_rect = fitz.Rect(0, 0, 595, 842)
    page.draw_rect(bg_rect, color=LIGHT_GRAY_COLOR, fill=LIGHT_GRAY_COLOR)
    
    # Add some normal text/content (high density)
    text_rect = fitz.Rect(100, 100, 495, 300)
    page.draw_rect(text_rect, color=(0, 0, 0), fill=(0, 0, 0))
    page.insert_text((100, 320), "Simulated document with very light background", 
                     fontsize=12, color=(0, 0, 0))
    
    doc.save('/tmp/demo_light_bg.pdf')
    doc.close()
    print("Created demonstration PDF: /tmp/demo_light_bg.pdf")
    return '/tmp/demo_light_bg.pdf'


def main():
    print("=" * 80)
    print("Real Ink Consumption Calculation - Demonstration")
    print("=" * 80)
    
    # Create demonstration PDF
    pdf_path = create_demonstration_pdf()
    
    print("\nThis demonstration shows how the new real ink consumption calculation")
    print("handles documents with very light pixels (below 1% coverage threshold).\n")
    
    print("Scenario: Document with very light background (0.5% gray - below 1% threshold)")
    print("  - Represents scanned documents with paper texture")
    print("  - Watermarks or very faint background elements")
    print("  - Anti-aliased edges of text")
    print()
    
    # Analyze with printer profile
    profile = PrinterProfile('inkjet_standard')
    analyzer = PDFInkAnalyzer(pdf_path, dpi=150, printer_profile=profile)
    results = analyzer.analyze()
    
    print("\n" + "=" * 80)
    print("Analysis Results:")
    print("=" * 80)
    
    for result in results:
        print(f"\nPage {result['page']}:")
        print(f"  CMYK Coverage:")
        print(f"    Cyan:    {result['cyan_avg']:6.2f}%")
        print(f"    Magenta: {result['magenta_avg']:6.2f}%")
        print(f"    Yellow:  {result['yellow_avg']:6.2f}%")
        print(f"    Black:   {result['black_avg']:6.2f}%")
        print(f"  Total Average Coverage: {result['tac_avg']:6.2f}%")
        print()
        print(f"  Real Ink Consumption (with 1% threshold):")
        print(f"    Cyan:    {result['ink_cyan_ml']:.6f} mL")
        print(f"    Magenta: {result['ink_magenta_ml']:.6f} mL")
        print(f"    Yellow:  {result['ink_yellow_ml']:.6f} mL")
        print(f"    Black:   {result['ink_black_ml']:.6f} mL")
        print(f"    Total:   {result['ink_total_ml']:.6f} mL")
    
    # Get summary for 100 copies
    summary = analyzer.get_summary(copies=100)
    
    print("\n" + "=" * 80)
    print("Summary for 100 copies:")
    print("=" * 80)
    print(f"  Total ink required: {summary['ink_total_ml_all']:.4f} mL")
    print(f"  Breakdown:")
    print(f"    Cyan:    {summary['ink_cyan_ml_total']:.4f} mL")
    print(f"    Magenta: {summary['ink_magenta_ml_total']:.4f} mL")
    print(f"    Yellow:  {summary['ink_yellow_ml_total']:.4f} mL")
    print(f"    Black:   {summary['ink_black_ml_total']:.4f} mL")
    
    print("\n" + "=" * 80)
    print("Key Benefits of Real Ink Consumption Calculation:")
    print("=" * 80)
    print("✓ Minimum 1% threshold filters out imperceptible colors")
    print("✓ Pixel-by-pixel analysis for accurate real-world estimates")
    print("✓ Better cost predictions for documents with subtle colors")
    print("✓ Accounts for actual printer behavior (no ink below threshold)")
    print("✓ More accurate than simple average-based calculations")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nDemo failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
