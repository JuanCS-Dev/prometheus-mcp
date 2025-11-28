"""
Configure logging to be CLEAN and BEAUTIFUL
"""
import logging
import os
import sys
import warnings

def setup_logging():
    """Setup logging with clean output."""
    # NUCLEAR OPTION: Silence EVERYTHING

    # 1. Logging
    logging.basicConfig(
        level=logging.ERROR,  # Only ERRORS
        format='%(message)s'
    )

    # 2. Silence ALL noisy libraries
    for logger_name in [
        'google', 'grpc', 'absl', 'urllib3', 'httpx',
        'google.auth', 'google.api_core', 'googleapiclient',
        'asyncio', 'aiohttp', 'charset_normalizer'
    ]:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)

    # 3. Python warnings
    warnings.filterwarnings('ignore')

    # 4. Redirect stderr temporarily to suppress gRPC C++ warnings
    # These happen BEFORE Python logging is setup
    import io
    class SuppressStderr:
        def __init__(self):
            self.original = sys.stderr
            self.devnull = io.StringIO()

        def __enter__(self):
            sys.stderr = self.devnull
            return self

        def __exit__(self, *args):
            sys.stderr = self.original

    # 5. Environment variables to silence gRPC
    os.environ['GRPC_VERBOSITY'] = 'ERROR'
    os.environ['GRPC_TRACE'] = ''
    os.environ['GLOG_minloglevel'] = '3'  # 3 = FATAL only

    # Only show our important messages
    logging.getLogger('jdev_cli').setLevel(logging.WARNING)

# Auto-setup on import
setup_logging()
