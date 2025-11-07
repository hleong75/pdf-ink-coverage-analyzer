# PDF Ink Coverage Analyzer

A Python tool to analyze CMYK ink coverage in PDF files, calculating tonal coverage percentages, Total Area Coverage (TAC), and ink consumption in milliliters to ensure compliance with printing standards and estimate printing costs.

## Features

- **CMYK Channel Analysis**: Calculate average ink percentage (tonal coverage) for each CMYK channel (Cyan, Magenta, Yellow, Black)
- **TAC Analysis**: Compute average and maximum Total Area Coverage (TAC) per pixel
- **Print Limit Verification**: Automatically check if TAC exceeds common printing limits (280%, 300%, 320%)
- **Ink Volume Calculation**: Calculate required ink volume in milliliters for printing one or multiple copies
- **Printer Profiles**: Support for different printer types (inkjet standard, photo, office, laser) with resolution awareness
- **Multiple Copies Support**: Calculate total ink consumption for batch printing jobs
- **Multiple Export Formats**: Export results to CSV or JSON for further analysis
- **Page-by-Page Analysis**: Detailed breakdown for each page in multi-page PDFs
- **Overall Summary**: Aggregate statistics across all pages with total ink requirements
- **Open Source**: Reproducible and customizable for your needs

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

### Calculate Ink Volume

Calculate required ink volume with a printer profile:

```bash
python pdf_ink_analyzer.py document.pdf --printer-profile inkjet_standard
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
                           [--copies COPIES] [--csv FILE] [--json FILE] 
                           [--no-summary] [--quiet] pdf_file

positional arguments:
  pdf_file              Path to PDF file to analyze

optional arguments:
  -h, --help            Show this help message and exit
  --dpi DPI             Resolution for rendering pages (default: 150)
  --printer-profile {inkjet_standard,inkjet_photo,inkjet_office,laser}
                        Printer profile for ink volume calculation
  --copies COPIES       Number of copies to calculate ink for (default: 1)
  --csv FILE            Export results to CSV file
  --json FILE           Export results to JSON file
  --no-summary          Do not include summary in JSON output
  --quiet, -q           Do not print results to console
```

## Printer Profiles

The tool supports different printer profiles for accurate ink volume calculation:

- **inkjet_standard**: Standard inkjet printer (4 picoliters per drop, 600 DPI)
- **inkjet_photo**: Photo inkjet printer (2 picoliters per drop, 1200 DPI)
- **inkjet_office**: Office inkjet printer (10 picoliters per drop, 300 DPI)
- **laser**: Laser/LED printer (600 DPI, toner-based calculation)

Each profile accounts for printer resolution and ink droplet size to provide accurate milliliter estimates.

## Output Format

### Console Output

The script displays detailed information for each page:

```
================================================================================
PDF Ink Coverage Analysis: document.pdf
Printer Profile: Standard inkjet printer (4pl drops, 600 DPI)
Calculating for 100 copies
================================================================================

Page 1:
  Cyan (C):     45.23%
  Magenta (M):  38.67%
  Yellow (Y):   42.18%
  Black (K):    15.92%
  TAC Average: 142.00%
  TAC Maximum: 285.50%

  Ink Volume (per copy):
    Cyan:      0.1250 mL
    Magenta:   0.1067 mL
    Yellow:    0.1164 mL
    Black:     0.0439 mL
    Total:     0.3920 mL

  ⚠️  CAUTION: TAC exceeds 280% limit!

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
Pages exceeding 280%:  1
Pages exceeding 300%:  0
Pages exceeding 320%:  0

Total Ink Volume (100 copies):
  Cyan:     12.5000 mL
  Magenta:  10.6700 mL
  Yellow:   11.6400 mL
  Black:     4.3900 mL
  Total:    39.2000 mL
================================================================================
```

### CSV Output

CSV files contain one row per page with the following columns:
- `page`: Page number
- `cyan_avg`: Average cyan coverage (%)
- `magenta_avg`: Average magenta coverage (%)
- `yellow_avg`: Average yellow coverage (%)
- `black_avg`: Average black coverage (%)
- `tac_avg`: Average TAC (%)
- `tac_max`: Maximum TAC (%)
- `exceeds_280`: Boolean flag
- `exceeds_300`: Boolean flag
- `exceeds_320`: Boolean flag
- `ink_cyan_ml`: Cyan ink volume in mL (if printer profile specified)
- `ink_magenta_ml`: Magenta ink volume in mL (if printer profile specified)
- `ink_yellow_ml`: Yellow ink volume in mL (if printer profile specified)
- `ink_black_ml`: Black ink volume in mL (if printer profile specified)
- `ink_total_ml`: Total ink volume in mL (if printer profile specified)

### JSON Output

JSON files include per-page data and an optional summary section:

```json
{
  "pdf_file": "document.pdf",
  "dpi": 150,
  "printer_profile": "Standard inkjet printer (4pl drops, 600 DPI)",
  "pages": [
    {
      "page": 1,
      "cyan_avg": 45.23,
      "magenta_avg": 38.67,
      "yellow_avg": 42.18,
      "black_avg": 15.92,
      "tac_avg": 142.00,
      "tac_max": 285.50,
      "exceeds_280": true,
      "exceeds_300": false,
      "exceeds_320": false,
      "ink_cyan_ml": 0.1250,
      "ink_magenta_ml": 0.1067,
      "ink_yellow_ml": 0.1164,
      "ink_black_ml": 0.0439,
      "ink_total_ml": 0.3920
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
    "pages_exceeding_280": 1,
    "pages_exceeding_300": 0,
    "pages_exceeding_320": 0,
    "ink_cyan_ml_total": 12.50,
    "ink_magenta_ml_total": 10.67,
    "ink_yellow_ml_total": 11.64,
    "ink_black_ml_total": 4.39,
    "ink_total_ml_all": 39.20,
    "printer_profile": "Standard Inkjet"
  }
}
```

## Understanding the Results

### CMYK Coverage

Each CMYK channel percentage represents the average ink density for that color across the entire page or document:
- **0%**: No ink (white)
- **100%**: Full ink coverage

### Total Area Coverage (TAC)

TAC is the sum of all four CMYK percentages for a given pixel. It indicates the total amount of ink that will be applied:

- **TAC < 280%**: Generally safe for most printing processes
- **280% < TAC < 300%**: May require attention, acceptable for some processes
- **300% < TAC < 320%**: High ink coverage, may cause drying issues
- **TAC > 320%**: Exceeds most printer limits, likely to cause problems

Common TAC limits by printing process:
- Web offset: 240-280%
- Sheet-fed offset: 300-320%
- Digital printing: 280-400% (varies by equipment)

### Ink Volume Calculation

When a printer profile is specified, the tool calculates the actual ink volume in milliliters needed for printing:

**For Inkjet Printers:**
- Calculation based on ink droplet size (picoliters) and printer resolution (DPI)
- Accounts for number of drops per pixel required for coverage
- Different profiles for standard, photo, and office inkjet printers

**For Laser Printers:**
- Calculation based on printed area and average toner consumption
- Accounts for printer resolution and toner density

The ink volume is calculated per page and can be scaled for multiple copies, making it ideal for:
- Estimating ink costs for print jobs
- Planning ink cartridge purchases
- Comparing printing costs across different printers
- Budgeting for large batch printing projects

## Use Cases

- **Prepress Verification**: Check if PDFs meet printing specifications before sending to press
- **Quality Control**: Automated analysis of large batches of documents
- **Cost Estimation**: Estimate ink consumption and cost for printing jobs based on actual printer profiles
- **Batch Printing**: Calculate total ink requirements for printing multiple copies
- **Ink Budget Planning**: Plan ink cartridge purchases based on predicted consumption
- **Standards Compliance**: Ensure documents comply with ISO 12647 or other printing standards
- **Troubleshooting**: Identify pages with excessive ink coverage that may cause printing issues

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