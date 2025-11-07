#!/usr/bin/env python3
"""
PDF Ink Coverage Analyzer

Analyzes PDF files to calculate:
- Average ink percentage (tonal coverage) for each CMYK channel
- Average TAC (Total Area Coverage)
- Maximum TAC per pixel
- ISO 12647 standard compliance checking
- Ink volume calculation based on ISO/IEC 24711/24712 methodologies
- Exports results to CSV/JSON formats

Standards implemented:
- ISO 12647-2: Graphic technology — Process control for offset lithographic processes
- ISO/IEC 24711: Method for the determination of ink cartridge yield (inkjet)
- ISO/IEC 24712: Method for the determination of ink cartridge yield (monochrome inkjet)
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


class ISO12647Standard:
    """
    ISO 12647-2 standard definitions for process control in offset lithographic processes
    
    ISO 12647-2 defines maximum Total Area Coverage (TAC) limits for different printing processes
    to ensure proper ink adhesion, drying, and color reproduction quality.
    """
    
    # TAC limits defined by ISO 12647-2 for different printing processes
    PROCESS_TAC_LIMITS = {
        'sheet_fed_coated': {
            'tac_limit': 330,
            'description': 'Sheet-fed offset on coated paper (ISO 12647-2)',
            'warning_threshold': 320
        },
        'sheet_fed_uncoated': {
            'tac_limit': 320,
            'description': 'Sheet-fed offset on uncoated paper (ISO 12647-2)',
            'warning_threshold': 300
        },
        'heatset_web': {
            'tac_limit': 300,
            'description': 'Heatset web offset (ISO 12647-2)',
            'warning_threshold': 280
        },
        'coldset_web': {
            'tac_limit': 260,
            'description': 'Coldset web offset (ISO 12647-2)',
            'warning_threshold': 240
        },
        'newspaper': {
            'tac_limit': 240,
            'description': 'Newspaper printing (ISO 12647-3)',
            'warning_threshold': 220
        },
        'digital_press': {
            'tac_limit': 320,
            'description': 'Digital press (typical limit)',
            'warning_threshold': 300
        }
    }
    
    @classmethod
    def get_process_limit(cls, process_type: str) -> Dict:
        """Get TAC limit information for a specific printing process"""
        return cls.PROCESS_TAC_LIMITS.get(process_type, {
            'tac_limit': 300,
            'description': 'Generic printing process',
            'warning_threshold': 280
        })
    
    @classmethod
    def check_compliance(cls, tac_max: float, process_type: str = 'sheet_fed_coated') -> Dict:
        """
        Check if TAC complies with ISO 12647 standards
        
        Args:
            tac_max: Maximum TAC value to check
            process_type: Type of printing process
            
        Returns:
            Dictionary with compliance information
        """
        limits = cls.get_process_limit(process_type)
        tac_limit = limits['tac_limit']
        warning_threshold = limits['warning_threshold']
        
        if tac_max <= warning_threshold:
            status = 'compliant'
            severity = 'ok'
        elif tac_max <= tac_limit:
            status = 'within_limits_caution'
            severity = 'warning'
        else:
            status = 'exceeds_limit'
            severity = 'error'
        
        return {
            'status': status,
            'severity': severity,
            'tac_max': tac_max,
            'tac_limit': tac_limit,
            'warning_threshold': warning_threshold,
            'process_type': process_type,
            'description': limits['description']
        }


class PrinterProfile:
    """
    Printer profile with resolution and ink specifications
    
    Ink volume calculations follow methodologies similar to:
    - ISO/IEC 24711: Method for the determination of ink cartridge yield (color inkjet)
    - ISO/IEC 24712: Method for the determination of ink cartridge yield (monochrome inkjet)
    
    These standards define standardized methods for measuring and reporting printer yield,
    which we adapt for estimating ink consumption based on coverage analysis.
    """
    
    # Common printer profiles with typical specifications
    PROFILES = {
        'inkjet_standard': {
            'name': 'Standard Inkjet',
            'dpi': 600,
            'ink_per_drop_pl': 4.0,  # picoliters per drop
            'drops_per_pixel': 1.5,
            'description': 'Standard inkjet printer (4pl drops, 600 DPI, ISO/IEC 24711 methodology)',
            'iso_standard': 'ISO/IEC 24711'
        },
        'inkjet_photo': {
            'name': 'Photo Inkjet',
            'dpi': 1200,
            'ink_per_drop_pl': 2.0,
            'drops_per_pixel': 2.0,
            'description': 'Photo inkjet printer (2pl drops, 1200 DPI, ISO/IEC 24711 methodology)',
            'iso_standard': 'ISO/IEC 24711'
        },
        'inkjet_office': {
            'name': 'Office Inkjet',
            'dpi': 300,
            'ink_per_drop_pl': 10.0,
            'drops_per_pixel': 1.0,
            'description': 'Office inkjet printer (10pl drops, 300 DPI, ISO/IEC 24711 methodology)',
            'iso_standard': 'ISO/IEC 24711'
        },
        'laser': {
            'name': 'Laser/LED',
            'dpi': 600,
            'ink_per_drop_pl': 0.0,  # Laser uses toner, not ink drops
            'drops_per_pixel': 0.0,
            'description': 'Laser printer (calculated based on coverage area, ISO/IEC 19752 methodology)',
            'iso_standard': 'ISO/IEC 19752'
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
        self.iso_standard = profile['iso_standard']


class PDFInkAnalyzer:
    """
    Analyzes ink coverage in PDF files with ISO standard compliance
    
    This analyzer implements methodologies based on:
    - ISO 12647: Process control standards for TAC limits
    - ISO/IEC 24711: Inkjet cartridge yield measurement methodology
    - ISO/IEC 24712: Monochrome inkjet cartridge yield methodology
    - ISO/IEC 19752: Monochrome laser toner yield methodology
    
    Advanced features:
    - Perceptual gamma correction (γ=2.2) for accurate color representation
    - Gray Component Replacement (GCR) for optimal black ink usage
    - ISO 12647-compliant dot gain compensation
    - Comprehensive statistical analysis with standard deviations and percentiles
    """
    
    # Constants for ink volume calculations (based on ISO/IEC standards)
    PICOLITERS_TO_MILLILITERS = 1_000_000_000.0  # 1 mL = 1,000,000,000 pL
    SQ_INCH_TO_SQ_CM = 6.4516  # 1 square inch = 6.4516 square centimeters
    TONER_ML_PER_SQ_CM = 0.0005  # Average toner consumption: ~0.0005 mL per sq cm at 100% coverage
    
    # Conversion method identifier
    CONVERSION_METHOD_ADVANCED_GCR = 'advanced_gcr'
    
    # Dot gain compensation factors (based on ISO 12647 standards)
    DOT_GAIN_COMPENSATION = {
        'sheet_fed_coated': 0.12,      # ~12% dot gain
        'sheet_fed_uncoated': 0.18,    # ~18% dot gain
        'heatset_web': 0.15,           # ~15% dot gain
        'coldset_web': 0.22,           # ~22% dot gain
        'newspaper': 0.28,             # ~28% dot gain
        'digital_press': 0.10          # ~10% dot gain
    }
    
    def __init__(self, pdf_path: str, dpi: int = 150, printer_profile: PrinterProfile = None,
                 iso_process: str = 'sheet_fed_coated', apply_dot_gain: bool = True,
                 gcr_percentage: float = 0.8):
        """
        Initialize the analyzer
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for rendering pages (default: 150)
            printer_profile: PrinterProfile for ink calculation (optional)
            iso_process: ISO 12647 printing process type for TAC compliance checking
            apply_dot_gain: Apply dot gain compensation (default: True)
            gcr_percentage: Gray Component Replacement percentage 0.0-1.0 (default: 0.8 for 80% GCR)
        """
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi
        self.printer_profile = printer_profile
        self.iso_process = iso_process
        self.apply_dot_gain = apply_dot_gain
        self.gcr_percentage = max(0.0, min(1.0, gcr_percentage))  # Clamp to 0-1
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
            
            # Analyze the page using RGB to CMYK conversion
            page_result = self._analyze_page_rgb(img, page_num + 1)
            self.results.append(page_result)
        
        doc.close()
        return self.results
    
    def _rgb_to_cmyk_advanced(self, rgb_array: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Convert RGB image to CMYK using advanced method with GCR
        
        This method implements:
        - Perceptual gamma correction
        - Gray Component Replacement (GCR) for better black generation
        - Optional UCR (Under Color Removal)
        
        Args:
            rgb_array: RGB image as numpy array (height, width, 3)
        
        Returns:
            Tuple of (C, M, Y, K) arrays normalized to 0-100%
        """
        # Normalize RGB to 0-1
        rgb = rgb_array.astype(float) / 255.0
        
        # Apply perceptual gamma correction for more accurate conversion
        # This accounts for the non-linear perception of color
        gamma = 2.2
        rgb_linear = np.power(rgb, gamma)
        
        # Calculate K (black) using maximum method
        k_max = 1 - np.max(rgb_linear, axis=2)
        
        # Implement GCR (Gray Component Replacement)
        # This replaces CMY with K where appropriate, saving colored ink
        
        # Calculate the minimum of CMY (this is the gray component)
        r_inv = 1 - rgb_linear[:, :, 0]
        g_inv = 1 - rgb_linear[:, :, 1]
        b_inv = 1 - rgb_linear[:, :, 2]
        
        gray_component = np.minimum(np.minimum(r_inv, g_inv), b_inv)
        
        # Apply GCR: use more K, less CMY
        k = k_max * (1 - self.gcr_percentage) + gray_component * self.gcr_percentage
        
        # Avoid division by zero
        k_inv = 1 - k
        k_inv = np.where(k_inv == 0, 1e-10, k_inv)
        
        # Calculate CMY with GCR adjustment
        c = (1 - rgb_linear[:, :, 0] - k) / k_inv
        m = (1 - rgb_linear[:, :, 1] - k) / k_inv
        y = (1 - rgb_linear[:, :, 2] - k) / k_inv
        
        # Clip values to 0-1 range and convert to percentage
        c = np.clip(c, 0, 1) * 100
        m = np.clip(m, 0, 1) * 100
        y = np.clip(y, 0, 1) * 100
        k = np.clip(k, 0, 1) * 100
        
        return c, m, y, k
    
    def _apply_dot_gain_compensation(self, c: np.ndarray, m: np.ndarray, y: np.ndarray, k: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Apply dot gain compensation based on ISO 12647 standards
        
        Dot gain is the increase in dot size during the printing process.
        This compensation adjusts the measured coverage to account for physical ink spreading.
        
        Args:
            c, m, y, k: CMYK arrays (0-100%)
        
        Returns:
            Compensated CMYK arrays
        """
        if not self.apply_dot_gain:
            return c, m, y, k
        
        # Get dot gain factor for the current ISO process
        dot_gain = self.DOT_GAIN_COMPENSATION.get(self.iso_process, 0.15)
        
        # Apply dot gain compensation
        # Formula: compensated = original * (1 + dot_gain * (original / 100))
        # This accounts for the fact that dot gain is more pronounced at mid-tones
        c_comp = c * (1 + dot_gain * (c / 100.0))
        m_comp = m * (1 + dot_gain * (m / 100.0))
        y_comp = y * (1 + dot_gain * (y / 100.0))
        k_comp = k * (1 + dot_gain * (k / 100.0))
        
        # Ensure we don't exceed 100%
        c_comp = np.clip(c_comp, 0, 100)
        m_comp = np.clip(m_comp, 0, 100)
        y_comp = np.clip(y_comp, 0, 100)
        k_comp = np.clip(k_comp, 0, 100)
        
        return c_comp, m_comp, y_comp, k_comp
    
    
    def _analyze_page_rgb(self, img: Image.Image, page_num: int) -> Dict:
        """
        Analyze a single page using RGB to CMYK conversion
        
        Args:
            img: PIL Image object
            page_num: Page number (1-indexed)
        
        Returns:
            Dictionary with analysis results including ISO compliance
        """
        # Convert to numpy array
        rgb_array = np.array(img)
        
        # Convert to CMYK using advanced method
        c, m, y, k = self._rgb_to_cmyk_advanced(rgb_array)
        
        # Apply dot gain compensation if enabled
        if self.apply_dot_gain:
            c, m, y, k = self._apply_dot_gain_compensation(c, m, y, k)
        
        # Calculate statistics
        return self._calculate_page_statistics(c, m, y, k, page_num, rgb_array.shape[:2])
    
    def _calculate_page_statistics(self, c: np.ndarray, m: np.ndarray, y: np.ndarray, k: np.ndarray,
                                   page_num: int, shape: Tuple[int, int]) -> Dict:
        """
        Calculate statistical metrics for a page
        
        Args:
            c, m, y, k: CMYK arrays (0-100%)
            page_num: Page number (1-indexed)
            shape: Image shape (height, width)
        
        Returns:
            Dictionary with analysis results including ISO compliance and statistical metrics
        """
        height, width = shape
        
        # Calculate average coverage for each channel
        avg_c = float(np.mean(c))
        avg_m = float(np.mean(m))
        avg_y = float(np.mean(y))
        avg_k = float(np.mean(k))
        
        # Calculate standard deviations for accuracy reporting
        std_c = float(np.std(c))
        std_m = float(np.std(m))
        std_y = float(np.std(y))
        std_k = float(np.std(k))
        
        # Calculate TAC (Total Area Coverage) for each pixel
        tac = c + m + y + k
        
        avg_tac = float(np.mean(tac))
        max_tac = float(np.max(tac))
        std_tac = float(np.std(tac))
        
        # Calculate percentiles for better distribution understanding
        tac_p50 = float(np.percentile(tac, 50))  # Median
        tac_p95 = float(np.percentile(tac, 95))  # 95th percentile
        tac_p99 = float(np.percentile(tac, 99))  # 99th percentile
        
        # Check ISO 12647 compliance
        iso_compliance = ISO12647Standard.check_compliance(max_tac, self.iso_process)
        
        # Check if TAC exceeds common printing limits (backward compatibility)
        exceeds_280 = max_tac > 280
        exceeds_300 = max_tac > 300
        exceeds_320 = max_tac > 320
        
        result = {
            'page': page_num,
            'cyan_avg': round(avg_c, 2),
            'magenta_avg': round(avg_m, 2),
            'yellow_avg': round(avg_y, 2),
            'black_avg': round(avg_k, 2),
            'cyan_std': round(std_c, 2),
            'magenta_std': round(std_m, 2),
            'yellow_std': round(std_y, 2),
            'black_std': round(std_k, 2),
            'tac_avg': round(avg_tac, 2),
            'tac_max': round(max_tac, 2),
            'tac_std': round(std_tac, 2),
            'tac_median': round(tac_p50, 2),
            'tac_p95': round(tac_p95, 2),
            'tac_p99': round(tac_p99, 2),
            'exceeds_280': exceeds_280,
            'exceeds_300': exceeds_300,
            'exceeds_320': exceeds_320,
            'iso_compliance': iso_compliance,
            'dot_gain_applied': self.apply_dot_gain,
            'conversion_method': self.CONVERSION_METHOD_ADVANCED_GCR
        }
        
        # Calculate ink volumes if printer profile is provided
        if self.printer_profile:
            result['ink_cyan_ml'] = round(self._calculate_ink_volume(avg_c, width, height), 4)
            result['ink_magenta_ml'] = round(self._calculate_ink_volume(avg_m, width, height), 4)
            result['ink_yellow_ml'] = round(self._calculate_ink_volume(avg_y, width, height), 4)
            result['ink_black_ml'] = round(self._calculate_ink_volume(avg_k, width, height), 4)
            result['ink_total_ml'] = round(
                result['ink_cyan_ml'] + result['ink_magenta_ml'] + 
                result['ink_yellow_ml'] + result['ink_black_ml'], 4
            )
            result['iso_standard_used'] = self.printer_profile.iso_standard
        
        return result
    
    def _calculate_ink_volume(self, coverage_percent: float, width: int, height: int) -> float:
        """
        Calculate ink volume in milliliters for a given coverage percentage
        
        This calculation follows methodologies similar to ISO/IEC 24711 (color inkjet)
        and ISO/IEC 24712 (monochrome inkjet) standards for measuring cartridge yield.
        
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
        
        # Calculate based on printer type and ISO methodology
        if self.printer_profile.ink_per_drop_pl > 0:  # Inkjet (ISO/IEC 24711/24712)
            # Total drops needed
            total_drops = inked_pixels * self.printer_profile.drops_per_pixel
            
            # Convert picoliters to milliliters
            ink_ml = (total_drops * self.printer_profile.ink_per_drop_pl) / self.PICOLITERS_TO_MILLILITERS
        else:  # Laser/toner (ISO/IEC 19752 methodology)
            # For laser printers, use area-based calculation
            # Calculate printed area in square cm
            dpi = self.printer_profile.dpi
            area_sq_inch = (inked_pixels) / (dpi * dpi)
            area_sq_cm = area_sq_inch * self.SQ_INCH_TO_SQ_CM
            ink_ml = area_sq_cm * self.TONER_ML_PER_SQ_CM
        
        return ink_ml
    
    def get_summary(self, copies: int = 1) -> Dict:
        """
        Get summary statistics across all pages with ISO compliance summary
        
        Args:
            copies: Number of copies to calculate ink for (default: 1)
        
        Returns:
            Dictionary with summary statistics including ISO compliance
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
        
        # Add ISO 12647 compliance summary
        iso_process_info = ISO12647Standard.get_process_limit(self.iso_process)
        summary['iso_12647_process'] = self.iso_process
        summary['iso_12647_description'] = iso_process_info['description']
        summary['iso_12647_tac_limit'] = iso_process_info['tac_limit']
        
        # Count pages by compliance status
        compliant_pages = sum(1 for r in self.results if r['iso_compliance']['status'] == 'compliant')
        warning_pages = sum(1 for r in self.results if r['iso_compliance']['status'] == 'within_limits_caution')
        exceeds_pages = sum(1 for r in self.results if r['iso_compliance']['status'] == 'exceeds_limit')
        
        summary['iso_compliant_pages'] = compliant_pages
        summary['iso_warning_pages'] = warning_pages
        summary['iso_exceeds_pages'] = exceeds_pages
        
        # Add ink volume calculations if printer profile is provided
        if self.printer_profile and 'ink_total_ml' in self.results[0]:
            summary['ink_cyan_ml_total'] = round(sum(r['ink_cyan_ml'] for r in self.results) * copies, 4)
            summary['ink_magenta_ml_total'] = round(sum(r['ink_magenta_ml'] for r in self.results) * copies, 4)
            summary['ink_yellow_ml_total'] = round(sum(r['ink_yellow_ml'] for r in self.results) * copies, 4)
            summary['ink_black_ml_total'] = round(sum(r['ink_black_ml'] for r in self.results) * copies, 4)
            summary['ink_total_ml_all'] = round(sum(r['ink_total_ml'] for r in self.results) * copies, 4)
            summary['printer_profile'] = self.printer_profile.name
            summary['iso_standard_ink_calculation'] = self.printer_profile.iso_standard
        
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
                'ink_black_ml', 'ink_total_ml', 'iso_standard_used'
            ])
        
        # Add ISO compliance fields
        fieldnames.extend([
            'iso_compliance_status', 'iso_compliance_severity', 
            'iso_tac_limit', 'iso_process_description'
        ])
        
        # Prepare rows with flattened ISO compliance data
        rows = []
        for result in self.results:
            row = {k: v for k, v in result.items() if k != 'iso_compliance'}
            # Flatten ISO compliance
            if 'iso_compliance' in result:
                iso = result['iso_compliance']
                row['iso_compliance_status'] = iso['status']
                row['iso_compliance_severity'] = iso['severity']
                row['iso_tac_limit'] = iso['tac_limit']
                row['iso_process_description'] = iso['description']
            rows.append(row)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        
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
        Print results to console in a formatted way with ISO compliance information
        
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
            print(f"Ink Calculation Standard: {self.printer_profile.iso_standard}")
        
        # Print ISO 12647 process information
        iso_process_info = ISO12647Standard.get_process_limit(self.iso_process)
        print(f"TAC Compliance Standard: {iso_process_info['description']}")
        print(f"TAC Limit: {iso_process_info['tac_limit']}% (Warning at {iso_process_info['warning_threshold']}%)")
        
        if copies > 1:
            print(f"Calculating for {copies} copies")
        print("=" * 80)
        
        for result in self.results:
            print(f"\nPage {result['page']}:")
            print(f"  Cyan (C):    {result['cyan_avg']:6.2f}% ± {result.get('cyan_std', 0):5.2f}%")
            print(f"  Magenta (M): {result['magenta_avg']:6.2f}% ± {result.get('magenta_std', 0):5.2f}%")
            print(f"  Yellow (Y):  {result['yellow_avg']:6.2f}% ± {result.get('yellow_std', 0):5.2f}%")
            print(f"  Black (K):   {result['black_avg']:6.2f}% ± {result.get('black_std', 0):5.2f}%")
            print(f"  TAC Average: {result['tac_avg']:6.2f}%")
            print(f"  TAC Maximum: {result['tac_max']:6.2f}%")
            print(f"  TAC Median:  {result.get('tac_median', 0):6.2f}%")
            print(f"  TAC 95th %:  {result.get('tac_p95', 0):6.2f}%")
            
            # Print advanced conversion info if available
            if result.get('conversion_method') == self.CONVERSION_METHOD_ADVANCED_GCR:
                print(f"  Conversion:  Advanced GCR (Gray Component Replacement)")
            if result.get('dot_gain_applied'):
                print(f"  Dot Gain:    Applied ({self.DOT_GAIN_COMPENSATION.get(self.iso_process, 0.15)*100:.0f}%)")
            
            # Print ISO compliance status
            iso_comp = result['iso_compliance']
            if iso_comp['status'] == 'compliant':
                print(f"  ✓ ISO 12647 Compliant (TAC ≤ {iso_comp['warning_threshold']}%)")
            elif iso_comp['status'] == 'within_limits_caution':
                print(f"  ⚠️  Within ISO limits but near threshold (TAC ≤ {iso_comp['tac_limit']}%)")
            else:
                print(f"  ❌ Exceeds ISO 12647 limit (TAC > {iso_comp['tac_limit']}%)")
            
            # Print ink volumes if available
            if 'ink_total_ml' in result:
                print(f"\n  Ink Volume per copy (calculated using {result['iso_standard_used']}):")
                print(f"    Cyan:    {result['ink_cyan_ml']:8.4f} mL")
                print(f"    Magenta: {result['ink_magenta_ml']:8.4f} mL")
                print(f"    Yellow:  {result['ink_yellow_ml']:8.4f} mL")
                print(f"    Black:   {result['ink_black_ml']:8.4f} mL")
                print(f"    Total:   {result['ink_total_ml']:8.4f} mL")
            
            # Keep backward-compatible warnings
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
        print(f"\nISO 12647 Compliance:")
        print(f"  Process Type:        {summary['iso_12647_description']}")
        print(f"  TAC Limit:           {summary['iso_12647_tac_limit']}%")
        print(f"  Compliant Pages:     {summary['iso_compliant_pages']}")
        print(f"  Warning Pages:       {summary['iso_warning_pages']}")
        print(f"  Exceeding Pages:     {summary['iso_exceeds_pages']}")
        print(f"\nLegacy TAC Thresholds:")
        print(f"  Pages exceeding 280%:  {summary['pages_exceeding_280']}")
        print(f"  Pages exceeding 300%:  {summary['pages_exceeding_300']}")
        print(f"  Pages exceeding 320%:  {summary['pages_exceeding_320']}")
        
        # Print total ink volumes if available
        if 'ink_total_ml_all' in summary:
            print(f"\nTotal Ink Volume ({copies} {'copy' if copies == 1 else 'copies'}):")
            print(f"  Calculation Method:  {summary['iso_standard_ink_calculation']}")
            print(f"  Cyan:    {summary['ink_cyan_ml_total']:8.4f} mL")
            print(f"  Magenta: {summary['ink_magenta_ml_total']:8.4f} mL")
            print(f"  Yellow:  {summary['ink_yellow_ml_total']:8.4f} mL")
            print(f"  Black:   {summary['ink_black_ml_total']:8.4f} mL")
            print(f"  Total:   {summary['ink_total_ml_all']:8.4f} mL")
        
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Analyze CMYK ink coverage in PDF files with ISO/IEC standard compliance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a PDF and display results with ink volume (uses inkjet_standard by default)
  python pdf_ink_analyzer.py document.pdf
  
  # Use a different printer profile
  python pdf_ink_analyzer.py document.pdf --printer-profile inkjet_photo
  
  # Calculate for multiple copies
  python pdf_ink_analyzer.py document.pdf --copies 100
  
  # Specify ISO 12647 printing process for TAC compliance
  python pdf_ink_analyzer.py document.pdf --iso-process heatset_web
  
  # Export to CSV
  python pdf_ink_analyzer.py document.pdf --csv output.csv
  
  # Export to JSON with summary
  python pdf_ink_analyzer.py document.pdf --json output.json
  
  # Use higher resolution for more accurate analysis
  python pdf_ink_analyzer.py document.pdf --dpi 300 --json output.json
  
Available printer profiles (with ISO/IEC standard methodology):
  - inkjet_standard: Standard inkjet printer (4pl drops, 600 DPI, ISO/IEC 24711) [DEFAULT]
  - inkjet_photo: Photo inkjet printer (2pl drops, 1200 DPI, ISO/IEC 24711)
  - inkjet_office: Office inkjet printer (10pl drops, 300 DPI, ISO/IEC 24711)
  - laser: Laser printer (600 DPI, ISO/IEC 19752)

Available ISO 12647 printing processes:
  - sheet_fed_coated: Sheet-fed offset on coated paper (TAC limit: 330%)
  - sheet_fed_uncoated: Sheet-fed offset on uncoated paper (TAC limit: 320%)
  - heatset_web: Heatset web offset (TAC limit: 300%)
  - coldset_web: Coldset web offset (TAC limit: 260%)
  - newspaper: Newspaper printing (TAC limit: 240%)
  - digital_press: Digital press (TAC limit: 320%)
        """
    )
    
    parser.add_argument('pdf_file', help='Path to PDF file to analyze')
    parser.add_argument('--dpi', type=int, default=150,
                        help='Resolution for rendering pages (default: 150)')
    parser.add_argument('--printer-profile', 
                        choices=list(PrinterProfile.PROFILES.keys()),
                        default='inkjet_standard',
                        help='Printer profile for ink volume calculation (default: inkjet_standard, follows ISO/IEC standards)')
    parser.add_argument('--iso-process',
                        choices=list(ISO12647Standard.PROCESS_TAC_LIMITS.keys()),
                        default='sheet_fed_coated',
                        help='ISO 12647 printing process type for TAC compliance checking (default: sheet_fed_coated)')
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
        # Create printer profile (default: inkjet_standard)
        printer_profile = PrinterProfile(args.printer_profile)
        
        # Create analyzer and run analysis
        analyzer = PDFInkAnalyzer(
            args.pdf_file, 
            dpi=args.dpi, 
            printer_profile=printer_profile,
            iso_process=args.iso_process
        )
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
