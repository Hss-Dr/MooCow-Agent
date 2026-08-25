# set global timezone
from time import tzset
tzset()

from .get_logger import get_logger
logger = get_logger()