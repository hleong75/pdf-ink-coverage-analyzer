#!/usr/bin/env python3
"""
Test script for cartridge configuration and cost calculation feature
"""

import sys
import json
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

from pdf_ink_analyzer import PDFInkAnalyzer, PrinterProfile, CartridgeConfig


def create_test_cartridge_config(output_path: str = "/tmp/test_cartridge_config.json"):
    """
    Create a test cartridge configuration file
    
    Args:
        output_path: Path where to save the test config
    """
    config = {
        "cartridge_configuration": {
            "cyan": {
                "pages_per_cartridge": 200,
                "price_per_cartridge": 25.00,
                "description": "Cyan cartridge test"
            },
            "magenta": {
                "pages_per_cartridge": 200,
                "price_per_cartridge": 25.00,
                "description": "Magenta cartridge test"
            },
            "yellow": {
                "pages_per_cartridge": 200,
                "price_per_cartridge": 25.00,
                "description": "Yellow cartridge test"
            },
            "black": {
                "pages_per_cartridge": 400,
                "price_per_cartridge": 30.00,
                "description": "Black cartridge test"
            }
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"Test cartridge config created: {output_path}")
    return output_path


def create_test_pdf(output_path: str = "/tmp/test_cost_document.pdf"):
    """
    Create a simple test PDF
    
    Args:
        output_path: Path where to save the test PDF
    """
    # Create a new PDF
    doc = fitz.open()
    
    # Page 1: Red rectangle
    page = doc.new_page(width=595, height=842)  # A4 size
    rect = fitz.Rect(100, 100, 400, 400)
    page.draw_rect(rect, color=(1, 0, 0), fill=(1, 0, 0))
    page.insert_text((100, 450), "Test Page 1: Red Rectangle", fontsize=16)
    
    # Page 2: Blue rectangle
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(100, 100, 400, 400)
    page.draw_rect(rect, color=(0, 0, 1), fill=(0, 0, 1))
    page.insert_text((100, 450), "Test Page 2: Blue Rectangle", fontsize=16)
    
    # Save the PDF
    doc.save(output_path)
    doc.close()
    
    print(f"Test PDF created: {output_path}")
    return output_path


def run_test():
    """Run the cartridge configuration test"""
    print("=" * 80)
    print("Cartridge Configuration and Cost Calculation - Test Suite")
    print("=" * 80)
    
    # Create test PDF
    print("\n1. Creating test PDF...")
    test_pdf = create_test_pdf()
    
    # Create test cartridge configuration
    print("\n2. Creating test cartridge configuration...")
    test_config = create_test_cartridge_config()
    
    # Test loading cartridge configuration
    print("\n3. Testing CartridgeConfig class...")
    cartridge_config = CartridgeConfig(test_config)
    assert cartridge_config.is_configured(), "CartridgeConfig should be configured"
    assert cartridge_config.cyan_pages == 200, "Cyan pages should be 200"
    assert cartridge_config.cyan_price == 25.00, "Cyan price should be 25.00"
    assert cartridge_config.black_pages == 400, "Black pages should be 400"
    assert cartridge_config.black_price == 30.00, "Black price should be 30.00"
    print("✓ CartridgeConfig loaded correctly")
    
    # Test analysis with cartridge configuration
    print("\n4. Testing analysis with cartridge configuration...")
    profile = PrinterProfile('inkjet_standard')
    analyzer = PDFInkAnalyzer(
        test_pdf, 
        dpi=150, 
        printer_profile=profile,
        cartridge_config=cartridge_config
    )
    results = analyzer.analyze()
    
    # Print results with cost information
    print("\n5. Analysis Results with Cost Information:")
    analyzer.print_results(copies=100)
    
    # Verify cost calculations are present in summary
    print("\n6. Verification of cost calculations:")
    summary = analyzer.get_summary(copies=100)
    
    assert 'total_cost' in summary, "Summary should include total_cost"
    assert summary['total_cost'] > 0, "Total cost should be positive"
    print(f"✓ Total cost calculated: ${summary['total_cost']:.2f}")
    
    if 'cyan_cartridges' in summary:
        assert summary['cyan_cartridges'] > 0, "Cyan cartridges should be positive"
        print(f"✓ Cyan cartridges: {summary['cyan_cartridges']:.4f} = ${summary['cyan_cost']:.2f}")
    
    if 'magenta_cartridges' in summary:
        assert summary['magenta_cartridges'] > 0, "Magenta cartridges should be positive"
        print(f"✓ Magenta cartridges: {summary['magenta_cartridges']:.4f} = ${summary['magenta_cost']:.2f}")
    
    if 'yellow_cartridges' in summary:
        assert summary['yellow_cartridges'] > 0, "Yellow cartridges should be positive"
        print(f"✓ Yellow cartridges: {summary['yellow_cartridges']:.4f} = ${summary['yellow_cost']:.2f}")
    
    if 'black_cartridges' in summary:
        assert summary['black_cartridges'] > 0, "Black cartridges should be positive"
        print(f"✓ Black cartridges: {summary['black_cartridges']:.4f} = ${summary['black_cost']:.2f}")
    
    # Test analysis without cartridge configuration (backward compatibility)
    print("\n7. Testing backward compatibility (without cartridge config)...")
    analyzer_no_config = PDFInkAnalyzer(
        test_pdf, 
        dpi=150, 
        printer_profile=profile
    )
    results_no_config = analyzer_no_config.analyze()
    summary_no_config = analyzer_no_config.get_summary(copies=100)
    
    assert 'total_cost' not in summary_no_config, "Summary without config should not include cost"
    assert 'ink_total_ml_all' in summary_no_config, "Summary should still include ink volume"
    print("✓ Backward compatibility verified - program works without cartridge config")
    
    # Export to JSON with cost information
    json_output = "/tmp/test_cost_results.json"
    print(f"\n8. Exporting to JSON with cost information: {json_output}")
    analyzer.export_to_json(json_output, copies=100)
    
    # Check that JSON file includes cost data
    with open(json_output, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    assert 'summary' in json_data, "JSON should include summary"
    assert 'total_cost' in json_data['summary'], "JSON summary should include total_cost"
    print(f"✓ JSON export includes cost information: ${json_data['summary']['total_cost']:.2f}")
    
    print("\n" + "=" * 80)
    print("All cartridge configuration tests passed! ✓")
    print("=" * 80)
    
    print("\nTest files created:")
    print(f"  - PDF: {test_pdf}")
    print(f"  - Config: {test_config}")
    print(f"  - JSON: {json_output}")


if __name__ == '__main__':
    try:
        run_test()
    except Exception as e:
        print(f"\nTest failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
