"""
Analytics Reports Module

This module contains report generation engines for the hosting transparency platform.
All reports focus on operational transparency and performance metrics without financial data.

Report Generators:
- professional_report_generator: Professional operational reports
"""

# Import report generators for easy access
try:
    from .professional_report_generator import *
except ImportError as e:
    import logging
    logging.warning(f"Some report generators could not be imported: {e}")