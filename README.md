# Fish Payslip Swap Tool

A Python script to swap name and personnel ID between two Iranian payslip PDFs.

## How to use

```bash
pip install pypdf
python swap_fish.py "10444483 (1).pdf" "67274571.pdf"
```

This will create:
- `10444483_(1)_swapped.pdf` - with name/ID from the second payslip
- `67274571_swapped.pdf` - with name/ID from the first payslip

All other fields (amounts, deductions, layout, fonts) remain unchanged.
