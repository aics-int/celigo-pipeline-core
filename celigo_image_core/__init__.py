__author__ = "AICS"

# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "1.0.0"


def get_module_version():
    return __version__


from .celigo_single_Image_core import CeligoSingleimageCore
from .celigo_orchestration import celigo_run_single, celigo_run_all

__all__ = ("CeligoSingleImageCore",'celigo_run_single','celigo_run_all')