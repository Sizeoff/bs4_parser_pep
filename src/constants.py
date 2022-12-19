from pathlib import Path

MAIN_DOC_URL = 'https://peps.python.org/'
PYTHON3_DOC_URL = 'https://docs.python.org/3/'
BASE_DIR = Path(__file__).parent
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
DT_FORMAT = '%d.%m.%Y %H:%M:%S'
LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
EXPECTED_STATUS = {'A': 0,
                   'D': 0,
                   'F': 0,
                   'P': 0,
                   'R': 0,
                   'S': 0,
                   'W': 0}
