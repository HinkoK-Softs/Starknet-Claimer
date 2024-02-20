import logging
from uuid import uuid4

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.CRITICAL,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('Starknet')
logger.setLevel(logging.INFO)
logging = logger
