import os
import sys

is_arc = os.path.basename(sys.executable).startswith('Arc')

NG_911_DIR = os.path.abspath(os.path.dirname(__file__))
from ilng911.core.database import NG911Data

try:
    ng911_db = NG911Data('test')
except Exception as e:
    ng911_db = None