# PDF Ink Coverage Analyzer

A Python tool to analyze CMYK ink coverage in PDF files, calculating tonal coverage percentages and Total Area Coverage (TAC) to ensure compliance with printing standards.

## Features

- **CMYK Channel Analysis**: Calculate average ink percentage (tonal coverage) for each CMYK channel (Cyan, Magenta, Yellow, Black)
- **TAC Analysis**: Compute average and maximum Total Area Coverage (TAC) per pixel
- **Print Limit Verification**: Automatically check if TAC exceeds common printing limits (280%, 300%, 320%)
- **Multiple Export Formats**: Export results to CSV or JSON for further analysis
- **Page-by-Page Analysis**: Detailed breakdown for each page in multi-page PDFs
- **Overall Summary**: Aggregate statistics across all pages
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

### Export to CSV

Export results to a CSV file for spreadsheet analysis:

```bash
python pdf_ink_analyzer.py document.pdf --csv output.csv
```

### Export to JSON

Export results to JSON with summary statistics:

```bash
python pdf_ink_analyzer.py document.pdf --json output.json
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
usage: pdf_ink_analyzer.py [-h] [--dpi DPI] [--csv FILE] [--json FILE] 
                           [--no-summary] [--quiet] pdf_file

positional arguments:
  pdf_file        Path to PDF file to analyze

optional arguments:
  -h, --help      Show this help message and exit
  --dpi DPI       Resolution for rendering pages (default: 150)
  --csv FILE      Export results to CSV file
  --json FILE     Export results to JSON file
  --no-summary    Do not include summary in JSON output
  --quiet, -q     Do not print results to console
```

## Output Format

### Console Output

The script displays detailed information for each page:

```
================================================================================
PDF Ink Coverage Analysis: document.pdf
================================================================================

Page 1:
  Cyan (C):     45.23%
  Magenta (M):  38.67%
  Yellow (Y):   42.18%
  Black (K):    15.92%
  TAC Average: 142.00%
  TAC Maximum: 285.50%
  ⚠️  CAUTION: TAC exceeds 280% limit!

--------------------------------------------------------------------------------
Overall Summary:
--------------------------------------------------------------------------------
Total Pages:           1
Cyan Average:          45.23%
Magenta Average:       38.67%
Yellow Average:        42.18%
Black Average:         15.92%
TAC Average Overall:  142.00%
TAC Maximum Overall:  285.50%
Pages exceeding 280%:  1
Pages exceeding 300%:  0
Pages exceeding 320%:  0
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

### JSON Output

JSON files include per-page data and an optional summary section:

```json
{
  "pdf_file": "document.pdf",
  "dpi": 150,
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
      "exceeds_320": false
    }
  ],
  "summary": {
    "total_pages": 1,
    "cyan_avg_overall": 45.23,
    "magenta_avg_overall": 38.67,
    "yellow_avg_overall": 42.18,
    "black_avg_overall": 15.92,
    "tac_avg_overall": 142.00,
    "tac_max_overall": 285.50,
    "pages_exceeding_280": 1,
    "pages_exceeding_300": 0,
    "pages_exceeding_320": 0
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

## Use Cases

- **Prepress Verification**: Check if PDFs meet printing specifications before sending to press
- **Quality Control**: Automated analysis of large batches of documents
- **Cost Estimation**: Estimate ink consumption for printing jobs
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