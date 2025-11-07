# PDF Ink Coverage Analyzer

A Python tool to analyze CMYK ink coverage in PDF files, calculating tonal coverage percentages, Total Area Coverage (TAC), and ink consumption in milliliters to ensure compliance with ISO/IEC printing standards and estimate printing costs.

## Features

- **CMYK Channel Analysis**: Calculate average ink percentage (tonal coverage) for each CMYK channel (Cyan, Magenta, Yellow, Black)
- **TAC Analysis**: Compute average and maximum Total Area Coverage (TAC) per pixel
- **ISO 12647 Compliance**: Automatically verify TAC compliance with ISO 12647 standards for different printing processes
- **ISO/IEC Ink Calculation Standards**: Calculate ink volume using methodologies based on ISO/IEC 24711 (color inkjet), ISO/IEC 24712 (monochrome inkjet), and ISO/IEC 19752 (laser toner)
- **Print Limit Verification**: Check if TAC exceeds industry-standard printing limits
- **Ink Volume Calculation**: Calculate required ink volume in milliliters for printing one or multiple copies
- **Printer Profiles**: Support for different printer types (inkjet standard, photo, office, laser) with resolution awareness
- **Multiple Printing Processes**: Support for different ISO 12647 printing processes (sheet-fed, web offset, newspaper, digital press)
- **Multiple Copies Support**: Calculate total ink consumption for batch printing jobs
- **Multiple Export Formats**: Export results to CSV or JSON for further analysis with ISO compliance data
- **Page-by-Page Analysis**: Detailed breakdown for each page in multi-page PDFs
- **Overall Summary**: Aggregate statistics across all pages with total ink requirements and ISO compliance summary
- **Open Source**: Reproducible and customizable for your needs

## ISO/IEC Standards Implemented

This tool implements methodologies and compliance checking based on the following international standards:

### ISO 12647 - Process Control for Offset Lithographic Processes

ISO 12647 defines standard TAC (Total Area Coverage) limits for different printing processes to ensure proper ink adhesion, drying, and color reproduction quality. The tool supports:

- **Sheet-fed offset on coated paper** (ISO 12647-2): TAC limit 330%
- **Sheet-fed offset on uncoated paper** (ISO 12647-2): TAC limit 320%
- **Heatset web offset** (ISO 12647-2): TAC limit 300%
- **Coldset web offset** (ISO 12647-2): TAC limit 260%
- **Newspaper printing** (ISO 12647-3): TAC limit 240%
- **Digital press**: TAC limit 320% (typical)

### ISO/IEC 24711 - Color Inkjet Cartridge Yield Measurement

Methodology for determining ink cartridge yield for color inkjet printers. The tool adapts these standardized measurement methods to estimate ink consumption based on coverage analysis.

### ISO/IEC 24712 - Monochrome Inkjet Cartridge Yield Measurement

Methodology for determining ink cartridge yield for monochrome inkjet printers. Used for black ink calculations.

### ISO/IEC 19752 - Monochrome Laser Toner Cartridge Yield Measurement

Methodology for determining toner cartridge yield for monochrome laser printers. The tool adapts these methods for toner consumption estimates.

## Requirements

- Python 3.7 or higher
- PyMuPDF (fitz)
- Pillow
- NumPy

## Installation

1. Clone this repository:
```bash
git clone https://github.com/hleong75/pdf-ink-coverage-analyzer.git
cd pdf-ink-coverage-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Analysis

Analyze a PDF and display results in the console:

```bash
python pdf_ink_analyzer.py document.pdf
```

### Calculate Ink Volume with ISO Standard Methodology

Calculate required ink volume using ISO/IEC 24711 methodology for inkjet:

```bash
python pdf_ink_analyzer.py document.pdf --printer-profile inkjet_standard
```

### Specify ISO 12647 Printing Process

Check TAC compliance for a specific printing process:

```bash
python pdf_ink_analyzer.py document.pdf --iso-process newspaper
```

### Multiple Copies

Calculate ink consumption for printing 100 copies:

```bash
python pdf_ink_analyzer.py document.pdf --printer-profile inkjet_photo --copies 100
```

### Export to CSV

Export results to a CSV file for spreadsheet analysis:

```bash
python pdf_ink_analyzer.py document.pdf --csv output.csv
```

### Export to JSON

Export results to JSON with summary statistics and ink calculations:

```bash
python pdf_ink_analyzer.py document.pdf --printer-profile inkjet_standard --copies 50 --json output.json
```

### High-Resolution Analysis

Use higher DPI for more accurate analysis (slower but more precise):

```bash
python pdf_ink_analyzer.py document.pdf --dpi 300 --json output.json
```

### Quiet Mode

Run analysis without console output (useful for batch processing):

```bash
python pdf_ink_analyzer.py document.pdf --csv output.csv --quiet
```

## Command Line Options

```
usage: pdf_ink_analyzer.py [-h] [--dpi DPI] 
                           [--printer-profile {inkjet_standard,inkjet_photo,inkjet_office,laser}]
                           [--iso-process {sheet_fed_coated,sheet_fed_uncoated,heatset_web,coldset_web,newspaper,digital_press}]
                           [--copies COPIES] [--csv FILE] [--json FILE] 
                           [--no-summary] [--quiet] pdf_file

positional arguments:
  pdf_file              Path to PDF file to analyze

optional arguments:
  -h, --help            Show this help message and exit
  --dpi DPI             Resolution for rendering pages (default: 150)
  --printer-profile {inkjet_standard,inkjet_photo,inkjet_office,laser}
                        Printer profile for ink volume calculation (uses ISO/IEC standards)
  --iso-process {sheet_fed_coated,sheet_fed_uncoated,heatset_web,coldset_web,newspaper,digital_press}
                        ISO 12647 printing process type for TAC compliance checking (default: sheet_fed_coated)
  --copies COPIES       Number of copies to calculate ink for (default: 1)
  --csv FILE            Export results to CSV file (includes ISO compliance data)
  --json FILE           Export results to JSON file (includes ISO compliance data)
  --no-summary          Do not include summary in JSON output
  --quiet, -q           Do not print results to console
```

## Printer Profiles

The tool supports different printer profiles for accurate ink volume calculation using ISO/IEC standard methodologies:

- **inkjet_standard**: Standard inkjet printer (4 picoliters per drop, 600 DPI) - uses ISO/IEC 24711 methodology
- **inkjet_photo**: Photo inkjet printer (2 picoliters per drop, 1200 DPI) - uses ISO/IEC 24711 methodology
- **inkjet_office**: Office inkjet printer (10 picoliters per drop, 300 DPI) - uses ISO/IEC 24711 methodology
- **laser**: Laser/LED printer (600 DPI, toner-based calculation) - uses ISO/IEC 19752 methodology

Each profile accounts for printer resolution and ink droplet size to provide accurate milliliter estimates based on standardized measurement methodologies.

## ISO 12647 Printing Processes

The tool supports different printing processes with specific TAC limits according to ISO 12647 standards:

- **sheet_fed_coated**: Sheet-fed offset on coated paper (TAC limit: 330%, Warning: 320%)
- **sheet_fed_uncoated**: Sheet-fed offset on uncoated paper (TAC limit: 320%, Warning: 300%)
- **heatset_web**: Heatset web offset (TAC limit: 300%, Warning: 280%)
- **coldset_web**: Coldset web offset (TAC limit: 260%, Warning: 240%)
- **newspaper**: Newspaper printing/ISO 12647-3 (TAC limit: 240%, Warning: 220%)
- **digital_press**: Digital press (TAC limit: 320%, Warning: 300%)

Select the appropriate process type using the `--iso-process` option to ensure compliance with the correct standard for your printing application.

## Output Format

### Console Output

The script displays detailed information for each page with ISO compliance status:

```
================================================================================
PDF Ink Coverage Analysis: document.pdf
Printer Profile: Standard inkjet printer (4pl drops, 600 DPI, ISO/IEC 24711 methodology)
Ink Calculation Standard: ISO/IEC 24711
TAC Compliance Standard: Sheet-fed offset on coated paper (ISO 12647-2)
TAC Limit: 330% (Warning at 320%)
Calculating for 100 copies
================================================================================

Page 1:
  Cyan (C):     45.23%
  Magenta (M):  38.67%
  Yellow (Y):   42.18%
  Black (K):    15.92%
  TAC Average: 142.00%
  TAC Maximum: 285.50%
  ✓ ISO 12647 Compliant (TAC ≤ 320%)

  Ink Volume per copy (calculated using ISO/IEC 24711):
    Cyan:      0.1250 mL
    Magenta:   0.1067 mL
    Yellow:    0.1164 mL
    Black:     0.0439 mL
    Total:     0.3920 mL

--------------------------------------------------------------------------------
Overall Summary:
--------------------------------------------------------------------------------
Total Pages:           1
Number of Copies:      100
Cyan Average:          45.23%
Magenta Average:       38.67%
Yellow Average:        42.18%
Black Average:         15.92%
TAC Average Overall:  142.00%
TAC Maximum Overall:  285.50%

ISO 12647 Compliance:
  Process Type:        Sheet-fed offset on coated paper (ISO 12647-2)
  TAC Limit:           330%
  Compliant Pages:     1
  Warning Pages:       0
  Exceeding Pages:     0

Legacy TAC Thresholds:
  Pages exceeding 280%:  0
  Pages exceeding 300%:  0
  Pages exceeding 320%:  0

Total Ink Volume (100 copies):
  Calculation Method:  ISO/IEC 24711
  Cyan:     12.5000 mL
  Magenta:  10.6700 mL
  Yellow:   11.6400 mL
  Black:     4.3900 mL
  Total:    39.2000 mL
================================================================================
```

### CSV Output

CSV files contain one row per page with the following columns including ISO compliance data:
- `page`: Page number
- `cyan_avg`: Average cyan coverage (%)
- `magenta_avg`: Average magenta coverage (%)
- `yellow_avg`: Average yellow coverage (%)
- `black_avg`: Average black coverage (%)
- `tac_avg`: Average TAC (%)
- `tac_max`: Maximum TAC (%)
- `exceeds_280`: Boolean flag (legacy threshold)
- `exceeds_300`: Boolean flag (legacy threshold)
- `exceeds_320`: Boolean flag (legacy threshold)
- `ink_cyan_ml`: Cyan ink volume in mL (if printer profile specified)
- `ink_magenta_ml`: Magenta ink volume in mL (if printer profile specified)
- `ink_yellow_ml`: Yellow ink volume in mL (if printer profile specified)
- `ink_black_ml`: Black ink volume in mL (if printer profile specified)
- `ink_total_ml`: Total ink volume in mL (if printer profile specified)
- `iso_standard_used`: ISO/IEC standard used for ink calculation
- `iso_compliance_status`: Compliance status (compliant, within_limits_caution, exceeds_limit)
- `iso_compliance_severity`: Severity level (ok, warning, error)
- `iso_tac_limit`: TAC limit for the selected ISO process
- `iso_process_description`: Description of the ISO 12647 printing process

### JSON Output

JSON files include per-page data with ISO compliance information and an optional summary section:

```json
{
  "pdf_file": "document.pdf",
  "dpi": 150,
  "printer_profile": "Standard inkjet printer (4pl drops, 600 DPI, ISO/IEC 24711 methodology)",
  "pages": [
    {
      "page": 1,
      "cyan_avg": 45.23,
      "magenta_avg": 38.67,
      "yellow_avg": 42.18,
      "black_avg": 15.92,
      "tac_avg": 142.00,
      "tac_max": 285.50,
      "exceeds_280": false,
      "exceeds_300": false,
      "exceeds_320": false,
      "iso_compliance": {
        "status": "compliant",
        "severity": "ok",
        "tac_max": 285.50,
        "tac_limit": 330,
        "warning_threshold": 320,
        "process_type": "sheet_fed_coated",
        "description": "Sheet-fed offset on coated paper (ISO 12647-2)"
      },
      "ink_cyan_ml": 0.1250,
      "ink_magenta_ml": 0.1067,
      "ink_yellow_ml": 0.1164,
      "ink_black_ml": 0.0439,
      "ink_total_ml": 0.3920,
      "iso_standard_used": "ISO/IEC 24711"
    }
  ],
  "summary": {
    "total_pages": 1,
    "copies": 100,
    "cyan_avg_overall": 45.23,
    "magenta_avg_overall": 38.67,
    "yellow_avg_overall": 42.18,
    "black_avg_overall": 15.92,
    "tac_avg_overall": 142.00,
    "tac_max_overall": 285.50,
    "pages_exceeding_280": 0,
    "pages_exceeding_300": 0,
    "pages_exceeding_320": 0,
    "iso_12647_process": "sheet_fed_coated",
    "iso_12647_description": "Sheet-fed offset on coated paper (ISO 12647-2)",
    "iso_12647_tac_limit": 330,
    "iso_compliant_pages": 1,
    "iso_warning_pages": 0,
    "iso_exceeds_pages": 0,
    "ink_cyan_ml_total": 12.50,
    "ink_magenta_ml_total": 10.67,
    "ink_yellow_ml_total": 11.64,
    "ink_black_ml_total": 4.39,
    "ink_total_ml_all": 39.20,
    "printer_profile": "Standard Inkjet",
    "iso_standard_ink_calculation": "ISO/IEC 24711"
  }
  }
}
```

## Understanding the Results

### CMYK Coverage

Each CMYK channel percentage represents the average ink density for that color across the entire page or document:
- **0%**: No ink (white)
- **100%**: Full ink coverage

### Total Area Coverage (TAC) and ISO 12647 Compliance

TAC is the sum of all four CMYK percentages for a given pixel. It indicates the total amount of ink that will be applied. The tool checks compliance against ISO 12647 standards:

**ISO 12647 TAC Limits by Printing Process:**
- **Sheet-fed offset (coated)**: 330% (ISO 12647-2)
- **Sheet-fed offset (uncoated)**: 320% (ISO 12647-2)
- **Heatset web offset**: 300% (ISO 12647-2)
- **Coldset web offset**: 260% (ISO 12647-2)
- **Newspaper printing**: 240% (ISO 12647-3)
- **Digital press**: 320% (typical limit)

**Compliance Status:**
- **✓ Compliant**: TAC is within the safe warning threshold
- **⚠️ Within limits but near threshold**: TAC exceeds warning threshold but is still within the process limit
- **❌ Exceeds limit**: TAC exceeds the ISO 12647 limit for the selected process

These limits are defined to ensure proper ink adhesion, drying, and color reproduction quality according to international standards.

### Ink Volume Calculation (ISO/IEC Standards)

When a printer profile is specified, the tool calculates the actual ink volume in milliliters needed for printing using standardized methodologies:

**For Inkjet Printers (ISO/IEC 24711/24712):**
- Calculation based on ink droplet size (picoliters) and printer resolution (DPI)
- Accounts for number of drops per pixel required for coverage
- Different profiles for standard, photo, and office inkjet printers
- Follows standardized measurement methodologies from ISO/IEC 24711 (color inkjet) and ISO/IEC 24712 (monochrome inkjet)

**For Laser Printers (ISO/IEC 19752):**
- Calculation based on printed area and average toner consumption
- Accounts for printer resolution and toner density
- Follows measurement methodology from ISO/IEC 19752 (monochrome laser toner)

The ink volume is calculated per page and can be scaled for multiple copies, making it ideal for:
- Estimating ink costs for print jobs based on ISO-standardized methodologies
- Planning ink cartridge purchases
- Comparing printing costs across different printers
- Budgeting for large batch printing projects
- Meeting ISO compliance requirements for printing operations

## Use Cases

- **Prepress Verification**: Check if PDFs meet ISO 12647 printing specifications before sending to press
- **Quality Control**: Automated analysis of large batches of documents with ISO compliance verification
- **Cost Estimation**: Estimate ink consumption and cost for printing jobs based on ISO/IEC standardized methodologies
- **Batch Printing**: Calculate total ink requirements for printing multiple copies
- **Ink Budget Planning**: Plan ink cartridge purchases based on predicted consumption using ISO standards
- **Standards Compliance**: Ensure documents comply with ISO 12647 or other international printing standards
- **Printing Process Selection**: Determine which ISO 12647 process is most appropriate for your document
- **Troubleshooting**: Identify pages with excessive ink coverage that may cause printing issues
- **Print Shop Management**: Track ink consumption across jobs for accurate billing and inventory management

## Technical Details

### RGB to CMYK Conversion

The tool converts RGB images to CMYK using the standard formula:

```
K = 1 - max(R, G, B)
C = (1 - R - K) / (1 - K)
M = (1 - G - K) / (1 - K)
Y = (1 - B - K) / (1 - K)
```

Note: PDF files may contain native CMYK data, but this tool analyzes the rendered RGB representation. For production use with CMYK PDFs, consider tools that can directly access CMYK color spaces.

### DPI Settings

The `--dpi` parameter affects analysis accuracy and speed:
- **72-150 DPI**: Fast, suitable for quick checks
- **150-300 DPI**: Good balance of speed and accuracy (recommended)
- **300+ DPI**: High accuracy, slower processing, best for final verification

## Limitations

- Analyzes rendered RGB representation of PDFs (not native CMYK if present)
- Spot colors are converted to CMYK equivalents
- Processing time increases with DPI and file size
- Memory usage depends on page size and DPI

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source and available for use under standard open source practices.

## Acknowledgments

Built with:
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF processing
- [Pillow](https://python-pillow.org/) for image handling
- [NumPy](https://numpy.org/) for efficient numerical computations