import os
import sys
import logging
import contextlib
import logging
import time
import traceback as tb
from io import StringIO
from ilng911.env import NG_911_DIR
from ilng911.utils import updir


logDir = os.path.join(updir(NG_911_DIR, 1), 'Logs')

default_format = '%(asctime)s - %(levelname)s - %(message)s'
date_format='%Y-%m-%d %H:%M:%S'

def timestamp(prefix: str, suffix='.log', fmt: str='%Y%m%d%H%M%S') -> str:
    return ''.join([prefix or '', time.strftime(fmt), suffix])

def log(msg, level='info'):
    """prints message to stdout and also to log file.

    Args:
        *args: the message arguments
        level (str, optional): [description]. Defaults to 'info'.
    """
    getattr(logging, level)(msg)

    if 'Arc' in os.path.basename(sys.executable):
        import arcpy
        arcpy.AddMessage(msg)
    else:
        print(msg)
        
def set_logger_context(prefix='SDE_Maintenance_', format=default_format, datefmt=date_format, level=logging.DEBUG, **kwargs):
    """sets up the basic configuration for the logger

    Args:
        prefix (str, optional): [description]. Defaults to 'SDE_Maintenance_'.
        format ([type], optional): [description]. Defaults to default_format.
        datefmt ([type], optional): [description]. Defaults to date_format.
        level ([type], optional): [description]. Defaults to logging.DEBUG.
    """
    log_file = os.path.join(logDir, timestamp(prefix, suffix='.log'))
    if not os.path.exists(logDir):
        os.makedirs(logDir)
    logging.basicConfig(filename=log_file, format=format, datefmt=date_format, level=level, **kwargs)


@contextlib.contextmanager
def log_context(prefix='SDE_Maintenance_', format=default_format, datefmt=date_format, level=logging.INFO, **kwargs):
    set_logger_context(prefix, format, datefmt, level, **kwargs)
    try:
        yield
    except Exception:
        # We want the _full_ traceback with the context
        # First we get the current call stack, which constitutes the "top",
        # it has the context up to the point where the context manager is used
        top_stack = StringIO()
        tb.print_stack(file=top_stack)
        top_lines = top_stack.getvalue().strip('\n').split('\n')
        top_stack.close()
        # Get "bottom" stack from the local error that happened
        # inside of the "with" block this wraps
        exc_type, exc_value, exc_traceback = sys.exc_info()
        bottom_stack = StringIO()
        tb.print_tb(exc_traceback, file=bottom_stack)
        bottom_lines = bottom_stack.getvalue().strip('\n').split('\n')
        # Glue together top and bottom where overlap is found
        bottom_cutoff = 0
        for i, line in enumerate(bottom_lines):
            if line in top_lines:
                # start of overlapping section, take overlap from bottom
                top_lines = top_lines[:top_lines.index(line)]
                bottom_cutoff = i
                break
        bottom_lines = bottom_lines[bottom_cutoff:]
        tb_lines = top_lines + bottom_lines

        tb_string = '\n'.join(
            ['Traceback (most recent call last):'] +
            tb_lines +
            ['{}: {}'.format(exc_type.__name__, str(exc_value))]
        )
        bottom_stack.close()
        # Log the combined stack
        log('Full Error Traceback:\n{}'.format(tb_string), level="error")
