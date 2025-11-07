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


class PDFInkAnalyzer:
    """Analyzes ink coverage in PDF files"""
    
    def __init__(self, pdf_path: str, dpi: int = 150):
        """
        Initialize the analyzer
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for rendering pages (default: 150)
        """
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi
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
    
    def _reduce_tac_gcr(self, c: np.ndarray, m: np.ndarray, y: np.ndarray, k: np.ndarray, 
                        target_tac: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Reduce TAC using GCR (Gray Component Replacement)
        
        Replaces common CMY components with black ink to reduce total ink coverage.
        
        Args:
            c, m, y, k: CMYK arrays (0-100%)
            target_tac: Target maximum TAC value
        
        Returns:
            Tuple of reduced (C, M, Y, K) arrays
        """
        # Calculate current TAC
        tac = c + m + y + k
        
        # Find pixels exceeding target TAC
        exceeds = tac > target_tac
        
        if not np.any(exceeds):
            return c, m, y, k
        
        # Copy arrays to avoid modifying originals
        c_new = c.copy()
        m_new = m.copy()
        y_new = y.copy()
        k_new = k.copy()
        
        # Vectorized GCR application
        # Find minimum of CMY (gray component) for all pixels
        gray = np.minimum(np.minimum(c, m), y)
        
        # Calculate how much to reduce for pixels exceeding target
        excess = np.maximum(0, tac - target_tac)
        reduction = np.minimum(gray, excess)
        
        # Apply reduction only where TAC exceeds target
        mask = exceeds.astype(float)
        c_new = c - reduction * mask
        m_new = m - reduction * mask
        y_new = y - reduction * mask
        k_new = np.minimum(100, k + reduction * mask)
        
        return c_new, m_new, y_new, k_new
    
    def _reduce_tac_ucr(self, c: np.ndarray, m: np.ndarray, y: np.ndarray, k: np.ndarray, 
                        target_tac: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Reduce TAC using UCR (Under Color Removal)
        
        Reduces CMY in shadow areas where black is present.
        
        Args:
            c, m, y, k: CMYK arrays (0-100%)
            target_tac: Target maximum TAC value
        
        Returns:
            Tuple of reduced (C, M, Y, K) arrays
        """
        # Calculate current TAC
        tac = c + m + y + k
        
        # Find pixels exceeding target TAC
        exceeds = tac > target_tac
        
        if not np.any(exceeds):
            return c, m, y, k
        
        # Copy arrays to avoid modifying originals
        c_new = c.copy()
        m_new = m.copy()
        y_new = y.copy()
        k_new = k.copy()
        
        # Vectorized UCR application
        # Calculate how much to reduce
        excess = np.maximum(0, tac - target_tac)
        
        # For UCR, reduce CMY proportionally to reach target TAC
        # The reduction is proportional to the CMY values and scaled by excess
        cmy_sum = c + m + y + 1e-10  # Avoid division by zero
        
        # Calculate how much each channel needs to be reduced
        # We need to reduce cmy_sum by 'excess' amount
        # Distribute the reduction proportionally
        reduction_ratio = excess / cmy_sum
        
        # Apply reduction only where TAC exceeds target
        mask = exceeds.astype(float)
        c_new = np.maximum(0, c - c * reduction_ratio * mask)
        m_new = np.maximum(0, m - m * reduction_ratio * mask)
        y_new = np.maximum(0, y - y * reduction_ratio * mask)
        
        return c_new, m_new, y_new, k_new
    
    def _cmyk_to_rgb(self, c: np.ndarray, m: np.ndarray, y: np.ndarray, k: np.ndarray) -> np.ndarray:
        """
        Convert CMYK to RGB
        
        Args:
            c, m, y, k: CMYK arrays (0-100%)
        
        Returns:
            RGB array (0-255)
        """
        # Normalize to 0-1
        c = c / 100.0
        m = m / 100.0
        y = y / 100.0
        k = k / 100.0
        
        # Convert to RGB
        r = (1 - c) * (1 - k)
        g = (1 - m) * (1 - k)
        b = (1 - y) * (1 - k)
        
        # Convert to 0-255 range
        rgb = np.stack([r, g, b], axis=2) * 255
        return rgb.astype(np.uint8)
    
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
        
        return {
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
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics across all pages
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {}
        
        return {
            'total_pages': len(self.results),
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
    
    def export_to_csv(self, output_path: str):
        """
        Export results to CSV file
        
        Args:
            output_path: Path to output CSV file
        """
        if not self.results:
            raise ValueError("No results to export. Run analyze() first.")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'page', 'cyan_avg', 'magenta_avg', 'yellow_avg', 'black_avg',
                'tac_avg', 'tac_max', 'exceeds_280', 'exceeds_300', 'exceeds_320'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"Results exported to CSV: {output_path}", file=sys.stderr)
    
    def export_to_json(self, output_path: str, include_summary: bool = True):
        """
        Export results to JSON file
        
        Args:
            output_path: Path to output JSON file
            include_summary: Include summary statistics (default: True)
        """
        if not self.results:
            raise ValueError("No results to export. Run analyze() first.")
        
        output = {
            'pdf_file': str(self.pdf_path),
            'dpi': self.dpi,
            'pages': self.results
        }
        
        if include_summary:
            output['summary'] = self.get_summary()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Results exported to JSON: {output_path}", file=sys.stderr)
    
    def reduce_tac_and_save(self, output_path: str, target_tac: float = 280, method: str = 'gcr') -> Dict:
        """
        Reduce TAC in PDF and save to new file
        
        Args:
            output_path: Path to save the reduced PDF
            target_tac: Target maximum TAC value (default: 280%)
            method: Reduction method - 'gcr' or 'ucr' (default: 'gcr')
        
        Returns:
            Dictionary with before/after statistics
        """
        if method not in ['gcr', 'ucr']:
            raise ValueError("Method must be 'gcr' or 'ucr'")
        
        print(f"Reducing TAC to {target_tac}% using {method.upper()} method...", file=sys.stderr)
        
        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF: {e}")
        
        # Create new PDF for output
        output_doc = fitz.open()
        
        before_stats = []
        after_stats = []
        
        for page_num in range(len(doc)):
            print(f"Processing page {page_num + 1}/{len(doc)}...", file=sys.stderr)
            page = doc[page_num]
            
            # Render page to RGB pixmap
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            rgb_array = np.array(img)
            
            # Convert to CMYK
            c, m, y, k = self._rgb_to_cmyk(rgb_array)
            
            # Store before statistics
            tac_before = c + m + y + k
            before_stats.append({
                'page': page_num + 1,
                'tac_avg': float(np.mean(tac_before)),
                'tac_max': float(np.max(tac_before))
            })
            
            # Apply TAC reduction
            if method == 'gcr':
                c_new, m_new, y_new, k_new = self._reduce_tac_gcr(c, m, y, k, target_tac)
            else:  # ucr
                c_new, m_new, y_new, k_new = self._reduce_tac_ucr(c, m, y, k, target_tac)
            
            # Store after statistics
            tac_after = c_new + m_new + y_new + k_new
            after_stats.append({
                'page': page_num + 1,
                'tac_avg': float(np.mean(tac_after)),
                'tac_max': float(np.max(tac_after))
            })
            
            # Convert back to RGB
            rgb_new = self._cmyk_to_rgb(c_new, m_new, y_new, k_new)
            
            # Create new PIL Image
            img_new = Image.fromarray(rgb_new, 'RGB')
            
            # Save to temporary bytes buffer
            from io import BytesIO
            img_buffer = BytesIO()
            img_new.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            
            # Create new page with same dimensions as original
            new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # Insert the reduced image
            new_page.insert_image(new_page.rect, stream=img_bytes)
        
        # Save the output PDF
        output_doc.save(output_path)
        output_doc.close()
        doc.close()
        
        # Calculate summary statistics
        avg_reduction_avg = np.mean([before_stats[i]['tac_avg'] - after_stats[i]['tac_avg'] 
                                      for i in range(len(before_stats))])
        avg_reduction_max = np.mean([before_stats[i]['tac_max'] - after_stats[i]['tac_max'] 
                                      for i in range(len(before_stats))])
        
        result = {
            'method': method.upper(),
            'target_tac': target_tac,
            'before': {
                'avg_tac': round(np.mean([s['tac_avg'] for s in before_stats]), 2),
                'max_tac': round(max([s['tac_max'] for s in before_stats]), 2)
            },
            'after': {
                'avg_tac': round(np.mean([s['tac_avg'] for s in after_stats]), 2),
                'max_tac': round(max([s['tac_max'] for s in after_stats]), 2)
            },
            'reduction': {
                'avg_tac': round(avg_reduction_avg, 2),
                'max_tac': round(avg_reduction_max, 2)
            },
            'output_file': output_path
        }
        
        print(f"\nTAC reduction complete! Saved to: {output_path}", file=sys.stderr)
        print(f"Average TAC: {result['before']['avg_tac']}% → {result['after']['avg_tac']}% "
              f"(-{result['reduction']['avg_tac']}%)", file=sys.stderr)
        print(f"Maximum TAC: {result['before']['max_tac']}% → {result['after']['max_tac']}% "
              f"(-{result['reduction']['max_tac']}%)", file=sys.stderr)
        
        return result
    
    def print_results(self):
        """Print results to console in a formatted way"""
        if not self.results:
            print("No results available. Run analyze() first.")
            return
        
        print("\n" + "=" * 80)
        print(f"PDF Ink Coverage Analysis: {self.pdf_path.name}")
        print("=" * 80)
        
        for result in self.results:
            print(f"\nPage {result['page']}:")
            print(f"  Cyan (C):    {result['cyan_avg']:6.2f}%")
            print(f"  Magenta (M): {result['magenta_avg']:6.2f}%")
            print(f"  Yellow (Y):  {result['yellow_avg']:6.2f}%")
            print(f"  Black (K):   {result['black_avg']:6.2f}%")
            print(f"  TAC Average: {result['tac_avg']:6.2f}%")
            print(f"  TAC Maximum: {result['tac_max']:6.2f}%")
            
            if result['exceeds_320']:
                print(f"  ⚠️  WARNING: TAC exceeds 320% limit!")
            elif result['exceeds_300']:
                print(f"  ⚠️  WARNING: TAC exceeds 300% limit!")
            elif result['exceeds_280']:
                print(f"  ⚠️  CAUTION: TAC exceeds 280% limit!")
        
        summary = self.get_summary()
        print("\n" + "-" * 80)
        print("Overall Summary:")
        print("-" * 80)
        print(f"Total Pages:           {summary['total_pages']}")
        print(f"Cyan Average:          {summary['cyan_avg_overall']:6.2f}%")
        print(f"Magenta Average:       {summary['magenta_avg_overall']:6.2f}%")
        print(f"Yellow Average:        {summary['yellow_avg_overall']:6.2f}%")
        print(f"Black Average:         {summary['black_avg_overall']:6.2f}%")
        print(f"TAC Average Overall:   {summary['tac_avg_overall']:6.2f}%")
        print(f"TAC Maximum Overall:   {summary['tac_max_overall']:6.2f}%")
        print(f"Pages exceeding 280%:  {summary['pages_exceeding_280']}")
        print(f"Pages exceeding 300%:  {summary['pages_exceeding_300']}")
        print(f"Pages exceeding 320%:  {summary['pages_exceeding_320']}")
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
  
  # Export to CSV
  python pdf_ink_analyzer.py document.pdf --csv output.csv
  
  # Export to JSON with summary
  python pdf_ink_analyzer.py document.pdf --json output.json
  
  # Use higher resolution for more accurate analysis
  python pdf_ink_analyzer.py document.pdf --dpi 300 --json output.json
  
  # Reduce TAC to 280% using GCR method
  python pdf_ink_analyzer.py document.pdf --reduce-tac 280 --output reduced.pdf
  
  # Reduce TAC using UCR method
  python pdf_ink_analyzer.py document.pdf --reduce-tac 300 --method ucr --output reduced.pdf
        """
    )
    
    parser.add_argument('pdf_file', help='Path to PDF file to analyze')
    parser.add_argument('--dpi', type=int, default=150,
                        help='Resolution for rendering pages (default: 150)')
    parser.add_argument('--csv', metavar='FILE',
                        help='Export results to CSV file')
    parser.add_argument('--json', metavar='FILE',
                        help='Export results to JSON file')
    parser.add_argument('--no-summary', action='store_true',
                        help='Do not include summary in JSON output')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Do not print results to console')
    parser.add_argument('--reduce-tac', type=float, metavar='LIMIT',
                        help='Reduce TAC to specified limit (e.g., 280) and save to new PDF')
    parser.add_argument('--output', '-o', metavar='FILE',
                        help='Output file path for reduced PDF (required with --reduce-tac)')
    parser.add_argument('--method', choices=['gcr', 'ucr'], default='gcr',
                        help='TAC reduction method: gcr (Gray Component Replacement) or ucr (Under Color Removal) (default: gcr)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.reduce_tac and not args.output:
        parser.error("--reduce-tac requires --output to be specified")
    
    if args.output and not args.reduce_tac:
        parser.error("--output requires --reduce-tac to be specified")
    
    try:
        # Create analyzer
        analyzer = PDFInkAnalyzer(args.pdf_file, dpi=args.dpi)
        
        # If TAC reduction is requested
        if args.reduce_tac:
            result = analyzer.reduce_tac_and_save(args.output, target_tac=args.reduce_tac, method=args.method)
            
            # Print reduction summary
            if not args.quiet:
                print("\n" + "=" * 80)
                print(f"TAC Reduction Summary")
                print("=" * 80)
                print(f"Method:           {result['method']}")
                print(f"Target TAC:       {result['target_tac']}%")
                print(f"\nBefore Reduction:")
                print(f"  Average TAC:    {result['before']['avg_tac']}%")
                print(f"  Maximum TAC:    {result['before']['max_tac']}%")
                print(f"\nAfter Reduction:")
                print(f"  Average TAC:    {result['after']['avg_tac']}%")
                print(f"  Maximum TAC:    {result['after']['max_tac']}%")
                print(f"\nReduction:")
                print(f"  Average TAC:    -{result['reduction']['avg_tac']}%")
                print(f"  Maximum TAC:    -{result['reduction']['max_tac']}%")
                print(f"\nOutput saved to: {result['output_file']}")
                print("=" * 80 + "\n")
        else:
            # Run normal analysis
            analyzer.analyze()
            
            # Print results to console unless quiet mode
            if not args.quiet:
                analyzer.print_results()
            
            # Export to CSV if requested
            if args.csv:
                analyzer.export_to_csv(args.csv)
            
            # Export to JSON if requested
            if args.json:
                analyzer.export_to_json(args.json, include_summary=not args.no_summary)
            
            # If neither export option specified and quiet mode, remind user
            if args.quiet and not args.csv and not args.json:
                print("Warning: Quiet mode enabled but no export format specified.", file=sys.stderr)
                print("Use --csv or --json to export results.", file=sys.stderr)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
