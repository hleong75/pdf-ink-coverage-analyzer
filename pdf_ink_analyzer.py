#!/usr/bin/env python3
"""
PDF Ink Coverage Analyzer

Analyzes PDF files to calculate:
- Average ink percentage (tonal coverage) for each CMYK channel
- Average TAC (Total Area Coverage)
- Maximum TAC per pixel
- Exports results to CSV/JSON formats
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import fitz  # PyMuPDF
    from PIL import Image
    import numpy as np
except ImportError as e:
    print(f"Error: Required library not found. Please install dependencies: pip install -r requirements.txt")
    print(f"Details: {e}")
    sys.exit(1)


class PrinterProfile:
    """Printer profile with resolution and ink specifications"""
    
    # Common printer profiles with typical specifications
    PROFILES = {
        'inkjet_standard': {
            'name': 'Standard Inkjet',
            'dpi': 600,
            'ink_per_drop_pl': 4.0,  # picoliters per drop
            'drops_per_pixel': 1.5,
            'description': 'Standard inkjet printer (4pl drops, 600 DPI)'
        },
        'inkjet_photo': {
            'name': 'Photo Inkjet',
            'dpi': 1200,
            'ink_per_drop_pl': 2.0,
            'drops_per_pixel': 2.0,
            'description': 'Photo inkjet printer (2pl drops, 1200 DPI)'
        },
        'inkjet_office': {
            'name': 'Office Inkjet',
            'dpi': 300,
            'ink_per_drop_pl': 10.0,
            'drops_per_pixel': 1.0,
            'description': 'Office inkjet printer (10pl drops, 300 DPI)'
        },
        'laser': {
            'name': 'Laser/LED',
            'dpi': 600,
            'ink_per_drop_pl': 0.0,  # Laser uses toner, not ink drops
            'drops_per_pixel': 0.0,
            'description': 'Laser printer (calculated based on coverage area)'
        }
    }
    
    def __init__(self, profile_name: str = 'inkjet_standard'):
        """
        Initialize printer profile
        
        Args:
            profile_name: Name of the predefined printer profile
        """
        if profile_name not in self.PROFILES:
            raise ValueError(f"Unknown profile: {profile_name}. Available: {list(self.PROFILES.keys())}")
        
        profile = self.PROFILES[profile_name]
        self.name = profile['name']
        self.dpi = profile['dpi']
        self.ink_per_drop_pl = profile['ink_per_drop_pl']
        self.drops_per_pixel = profile['drops_per_pixel']
        self.description = profile['description']


class PDFInkAnalyzer:
    """Analyzes ink coverage in PDF files"""
    
    # Constants for ink volume calculations
    PICOLITERS_TO_MILLILITERS = 1_000_000_000.0  # 1 mL = 1,000,000,000 pL
    SQ_INCH_TO_SQ_CM = 6.4516  # 1 square inch = 6.4516 square centimeters
    TONER_ML_PER_SQ_CM = 0.0005  # Average toner consumption: ~0.0005 mL per sq cm at 100% coverage
    
    def __init__(self, pdf_path: str, dpi: int = 150, printer_profile: PrinterProfile = None):
        """
        Initialize the analyzer
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for rendering pages (default: 150)
            printer_profile: PrinterProfile for ink calculation (optional)
        """
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi
        self.printer_profile = printer_profile
        self.results = []
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def analyze(self) -> List[Dict]:
        """
        Analyze all pages in the PDF
        
        Returns:
            List of dictionaries containing analysis results for each page
        """
        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF: {e}")
        
        self.results = []
        
        for page_num in range(len(doc)):
            print(f"Analyzing page {page_num + 1}/{len(doc)}...", file=sys.stderr)
            page = doc[page_num]
            
            # Render page to RGB pixmap
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Analyze the page
            page_result = self._analyze_page(img, page_num + 1)
            self.results.append(page_result)
        
        doc.close()
        return self.results
    
    def _rgb_to_cmyk(self, rgb_array: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Convert RGB image to CMYK
        
        Args:
            rgb_array: RGB image as numpy array (height, width, 3)
        
        Returns:
            Tuple of (C, M, Y, K) arrays normalized to 0-100%
        """
        # Normalize RGB to 0-1
        rgb = rgb_array.astype(float) / 255.0
        
        # Calculate K (black)
        k = 1 - np.max(rgb, axis=2)
        
        # Avoid division by zero
        k_inv = 1 - k
        k_inv = np.where(k_inv == 0, 1e-10, k_inv)
        
        # Calculate CMY
        c = (1 - rgb[:, :, 0] - k) / k_inv
        m = (1 - rgb[:, :, 1] - k) / k_inv
        y = (1 - rgb[:, :, 2] - k) / k_inv
        
        # Clip values to 0-1 range and convert to percentage
        c = np.clip(c, 0, 1) * 100
        m = np.clip(m, 0, 1) * 100
        y = np.clip(y, 0, 1) * 100
        k = k * 100
        
        return c, m, y, k
    
    def _calculate_ink_volume(self, coverage_percent: float, width: int, height: int) -> float:
        """
        Calculate ink volume in milliliters for a given coverage percentage
        
        Args:
            coverage_percent: Percentage of ink coverage (0-100)
            width: Image width in pixels
            height: Image height in pixels
        
        Returns:
            Ink volume in milliliters
        """
        if not self.printer_profile:
            return 0.0
        
        # Total pixels in the image
        total_pixels = width * height
        
        # Pixels that need ink based on coverage percentage
        inked_pixels = total_pixels * (coverage_percent / 100.0)
        
        # Calculate based on printer type
        if self.printer_profile.ink_per_drop_pl > 0:  # Inkjet
            # Total drops needed
            total_drops = inked_pixels * self.printer_profile.drops_per_pixel
            
            # Convert picoliters to milliliters
            ink_ml = (total_drops * self.printer_profile.ink_per_drop_pl) / self.PICOLITERS_TO_MILLILITERS
        else:  # Laser/toner
            # For laser printers, use area-based calculation
            # Calculate printed area in square cm
            dpi = self.printer_profile.dpi
            area_sq_inch = (inked_pixels) / (dpi * dpi)
            area_sq_cm = area_sq_inch * self.SQ_INCH_TO_SQ_CM
            ink_ml = area_sq_cm * self.TONER_ML_PER_SQ_CM
        
        return ink_ml
    
    def _analyze_page(self, img: Image.Image, page_num: int) -> Dict:
        """
        Analyze a single page
        
        Args:
            img: PIL Image object
            page_num: Page number (1-indexed)
        
        Returns:
            Dictionary with analysis results
        """
        # Convert to numpy array
        rgb_array = np.array(img)
        
        # Convert to CMYK
        c, m, y, k = self._rgb_to_cmyk(rgb_array)
        
        # Calculate average coverage for each channel
        avg_c = float(np.mean(c))
        avg_m = float(np.mean(m))
        avg_y = float(np.mean(y))
        avg_k = float(np.mean(k))
        
        # Calculate TAC (Total Area Coverage) for each pixel
        tac = c + m + y + k
        
        avg_tac = float(np.mean(tac))
        max_tac = float(np.max(tac))
        
        # Check if TAC exceeds common printing limits
        exceeds_280 = max_tac > 280
        exceeds_300 = max_tac > 300
        exceeds_320 = max_tac > 320
        
        result = {
            'page': page_num,
            'cyan_avg': round(avg_c, 2),
            'magenta_avg': round(avg_m, 2),
            'yellow_avg': round(avg_y, 2),
            'black_avg': round(avg_k, 2),
            'tac_avg': round(avg_tac, 2),
            'tac_max': round(max_tac, 2),
            'exceeds_280': exceeds_280,
            'exceeds_300': exceeds_300,
            'exceeds_320': exceeds_320
        }
        
        # Calculate ink volumes if printer profile is provided
        if self.printer_profile:
            height, width = rgb_array.shape[:2]
            result['ink_cyan_ml'] = round(self._calculate_ink_volume(avg_c, width, height), 4)
            result['ink_magenta_ml'] = round(self._calculate_ink_volume(avg_m, width, height), 4)
            result['ink_yellow_ml'] = round(self._calculate_ink_volume(avg_y, width, height), 4)
            result['ink_black_ml'] = round(self._calculate_ink_volume(avg_k, width, height), 4)
            result['ink_total_ml'] = round(
                result['ink_cyan_ml'] + result['ink_magenta_ml'] + 
                result['ink_yellow_ml'] + result['ink_black_ml'], 4
            )
        
        return result
    
    def get_summary(self, copies: int = 1) -> Dict:
        """
        Get summary statistics across all pages
        
        Args:
            copies: Number of copies to calculate ink for (default: 1)
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {}
        
        summary = {
            'total_pages': len(self.results),
            'copies': copies,
            'cyan_avg_overall': round(np.mean([r['cyan_avg'] for r in self.results]), 2),
            'magenta_avg_overall': round(np.mean([r['magenta_avg'] for r in self.results]), 2),
            'yellow_avg_overall': round(np.mean([r['yellow_avg'] for r in self.results]), 2),
            'black_avg_overall': round(np.mean([r['black_avg'] for r in self.results]), 2),
            'tac_avg_overall': round(np.mean([r['tac_avg'] for r in self.results]), 2),
            'tac_max_overall': round(max([r['tac_max'] for r in self.results]), 2),
            'pages_exceeding_280': sum(1 for r in self.results if r['exceeds_280']),
            'pages_exceeding_300': sum(1 for r in self.results if r['exceeds_300']),
            'pages_exceeding_320': sum(1 for r in self.results if r['exceeds_320'])
        }
        
        # Add ink volume calculations if printer profile is provided
        if self.printer_profile and 'ink_total_ml' in self.results[0]:
            summary['ink_cyan_ml_total'] = round(sum(r['ink_cyan_ml'] for r in self.results) * copies, 4)
            summary['ink_magenta_ml_total'] = round(sum(r['ink_magenta_ml'] for r in self.results) * copies, 4)
            summary['ink_yellow_ml_total'] = round(sum(r['ink_yellow_ml'] for r in self.results) * copies, 4)
            summary['ink_black_ml_total'] = round(sum(r['ink_black_ml'] for r in self.results) * copies, 4)
            summary['ink_total_ml_all'] = round(sum(r['ink_total_ml'] for r in self.results) * copies, 4)
            summary['printer_profile'] = self.printer_profile.name
        
        return summary
    
    def export_to_csv(self, output_path: str):
        """
        Export results to CSV file
        
        Args:
            output_path: Path to output CSV file
        """
        if not self.results:
            raise ValueError("No results to export. Run analyze() first.")
        
        # Determine fieldnames based on whether ink volumes are present
        fieldnames = [
            'page', 'cyan_avg', 'magenta_avg', 'yellow_avg', 'black_avg',
            'tac_avg', 'tac_max', 'exceeds_280', 'exceeds_300', 'exceeds_320'
        ]
        
        # Add ink volume fields if present
        if self.results and 'ink_total_ml' in self.results[0]:
            fieldnames.extend([
                'ink_cyan_ml', 'ink_magenta_ml', 'ink_yellow_ml', 
                'ink_black_ml', 'ink_total_ml'
            ])
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"Results exported to CSV: {output_path}", file=sys.stderr)
    
    def export_to_json(self, output_path: str, include_summary: bool = True, copies: int = 1):
        """
        Export results to JSON file
        
        Args:
            output_path: Path to output JSON file
            include_summary: Include summary statistics (default: True)
            copies: Number of copies for ink calculation (default: 1)
        """
        if not self.results:
            raise ValueError("No results to export. Run analyze() first.")
        
        output = {
            'pdf_file': str(self.pdf_path),
            'dpi': self.dpi,
            'pages': self.results
        }
        
        if self.printer_profile:
            output['printer_profile'] = self.printer_profile.description
        
        if include_summary:
            output['summary'] = self.get_summary(copies)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Results exported to JSON: {output_path}", file=sys.stderr)
    
    def print_results(self, copies: int = 1):
        """
        Print results to console in a formatted way
        
        Args:
            copies: Number of copies for ink calculation (default: 1)
        """
        if not self.results:
            print("No results available. Run analyze() first.")
            return
        
        print("\n" + "=" * 80)
        print(f"PDF Ink Coverage Analysis: {self.pdf_path.name}")
        if self.printer_profile:
            print(f"Printer Profile: {self.printer_profile.description}")
        if copies > 1:
            print(f"Calculating for {copies} copies")
        print("=" * 80)
        
        for result in self.results:
            print(f"\nPage {result['page']}:")
            print(f"  Cyan (C):    {result['cyan_avg']:6.2f}%")
            print(f"  Magenta (M): {result['magenta_avg']:6.2f}%")
            print(f"  Yellow (Y):  {result['yellow_avg']:6.2f}%")
            print(f"  Black (K):   {result['black_avg']:6.2f}%")
            print(f"  TAC Average: {result['tac_avg']:6.2f}%")
            print(f"  TAC Maximum: {result['tac_max']:6.2f}%")
            
            # Print ink volumes if available
            if 'ink_total_ml' in result:
                print(f"\n  Ink Volume (per copy):")
                print(f"    Cyan:    {result['ink_cyan_ml']:8.4f} mL")
                print(f"    Magenta: {result['ink_magenta_ml']:8.4f} mL")
                print(f"    Yellow:  {result['ink_yellow_ml']:8.4f} mL")
                print(f"    Black:   {result['ink_black_ml']:8.4f} mL")
                print(f"    Total:   {result['ink_total_ml']:8.4f} mL")
            
            if result['exceeds_320']:
                print(f"  ⚠️  WARNING: TAC exceeds 320% limit!")
            elif result['exceeds_300']:
                print(f"  ⚠️  WARNING: TAC exceeds 300% limit!")
            elif result['exceeds_280']:
                print(f"  ⚠️  CAUTION: TAC exceeds 280% limit!")
        
        summary = self.get_summary(copies)
        print("\n" + "-" * 80)
        print("Overall Summary:")
        print("-" * 80)
        print(f"Total Pages:           {summary['total_pages']}")
        if copies > 1:
            print(f"Number of Copies:      {copies}")
        print(f"Cyan Average:          {summary['cyan_avg_overall']:6.2f}%")
        print(f"Magenta Average:       {summary['magenta_avg_overall']:6.2f}%")
        print(f"Yellow Average:        {summary['yellow_avg_overall']:6.2f}%")
        print(f"Black Average:         {summary['black_avg_overall']:6.2f}%")
        print(f"TAC Average Overall:   {summary['tac_avg_overall']:6.2f}%")
        print(f"TAC Maximum Overall:   {summary['tac_max_overall']:6.2f}%")
        print(f"Pages exceeding 280%:  {summary['pages_exceeding_280']}")
        print(f"Pages exceeding 300%:  {summary['pages_exceeding_300']}")
        print(f"Pages exceeding 320%:  {summary['pages_exceeding_320']}")
        
        # Print total ink volumes if available
        if 'ink_total_ml_all' in summary:
            print(f"\nTotal Ink Volume ({copies} {'copy' if copies == 1 else 'copies'}):")
            print(f"  Cyan:    {summary['ink_cyan_ml_total']:8.4f} mL")
            print(f"  Magenta: {summary['ink_magenta_ml_total']:8.4f} mL")
            print(f"  Yellow:  {summary['ink_yellow_ml_total']:8.4f} mL")
            print(f"  Black:   {summary['ink_black_ml_total']:8.4f} mL")
            print(f"  Total:   {summary['ink_total_ml_all']:8.4f} mL")
        
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Analyze CMYK ink coverage in PDF files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a PDF and display results
  python pdf_ink_analyzer.py document.pdf
  
  # Calculate ink volume with printer profile
  python pdf_ink_analyzer.py document.pdf --printer-profile inkjet_standard
  
  # Calculate for multiple copies
  python pdf_ink_analyzer.py document.pdf --printer-profile inkjet_photo --copies 100
  
  # Export to CSV
  python pdf_ink_analyzer.py document.pdf --csv output.csv
  
  # Export to JSON with summary
  python pdf_ink_analyzer.py document.pdf --json output.json
  
  # Use higher resolution for more accurate analysis
  python pdf_ink_analyzer.py document.pdf --dpi 300 --json output.json
  
Available printer profiles:
  - inkjet_standard: Standard inkjet printer (4pl drops, 600 DPI)
  - inkjet_photo: Photo inkjet printer (2pl drops, 1200 DPI)
  - inkjet_office: Office inkjet printer (10pl drops, 300 DPI)
  - laser: Laser printer (600 DPI, toner-based)
        """
    )
    
    parser.add_argument('pdf_file', help='Path to PDF file to analyze')
    parser.add_argument('--dpi', type=int, default=150,
                        help='Resolution for rendering pages (default: 150)')
    parser.add_argument('--printer-profile', 
                        choices=list(PrinterProfile.PROFILES.keys()),
                        help='Printer profile for ink volume calculation')
    parser.add_argument('--copies', type=int, default=1,
                        help='Number of copies to calculate ink for (default: 1)')
    parser.add_argument('--csv', metavar='FILE',
                        help='Export results to CSV file')
    parser.add_argument('--json', metavar='FILE',
                        help='Export results to JSON file')
    parser.add_argument('--no-summary', action='store_true',
                        help='Do not include summary in JSON output')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Do not print results to console')
    
    args = parser.parse_args()
    
    # Validate copies
    if args.copies < 1:
        print("Error: Number of copies must be at least 1", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Create printer profile if specified
        printer_profile = None
        if args.printer_profile:
            printer_profile = PrinterProfile(args.printer_profile)
        
        # Create analyzer and run analysis
        analyzer = PDFInkAnalyzer(args.pdf_file, dpi=args.dpi, printer_profile=printer_profile)
        analyzer.analyze()
        
        # Print results to console unless quiet mode
        if not args.quiet:
            analyzer.print_results(copies=args.copies)
        
        # Export to CSV if requested
        if args.csv:
            analyzer.export_to_csv(args.csv)
        
        # Export to JSON if requested
        if args.json:
            analyzer.export_to_json(args.json, include_summary=not args.no_summary, copies=args.copies)
        
        # If neither export option specified and quiet mode, remind user
        if args.quiet and not args.csv and not args.json:
            print("Warning: Quiet mode enabled but no export format specified.", file=sys.stderr)
            print("Use --csv or --json to export results.", file=sys.stderr)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
