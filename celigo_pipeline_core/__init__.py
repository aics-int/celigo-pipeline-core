__author__ = "AICS"

# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "1.0.0"


def get_module_version():
    return __version__



from .celigo_single_image.celigo_single_image_core import (
    CeligoSingleImageCore,
)

from celigo_orchestration import *

__all__ = "CeligoSingleImageCore"
