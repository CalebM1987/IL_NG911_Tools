import os

NG_911_DIR = os.path.abspath(os.path.dirname(__file__))
from ilng911.core.database import NG911Data

ng_911db = NG911Data('test')