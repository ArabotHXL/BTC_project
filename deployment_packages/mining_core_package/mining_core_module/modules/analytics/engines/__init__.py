"""
Analytics Engines Module

This module contains pure analytical computation engines for the hosting transparency platform.
These engines focus on data analysis without any financial flows or payment processing.

Engines:
- analytics_engine: Core market analytics and data collection
- historical_data_engine: Historical data processing and analysis
- advanced_algorithm_engine: Advanced computational algorithms
"""

# Import engines for easy access
try:
    from .analytics_engine import *
    from .historical_data_engine import *  
    from .advanced_algorithm_engine import *
except ImportError as e:
    import logging
    logging.warning(f"Some analytics engines could not be imported: {e}")