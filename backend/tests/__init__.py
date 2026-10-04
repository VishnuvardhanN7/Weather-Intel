import os
import sys

# Allow tests to be run directly from the backend directory without
# installing the package, e.g.  python -m unittest discover tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))