__author__ = "AICS"

# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "2.0.0"


def get_module_version():
    return __version__


from .celigo_orchestration import (
    job_complete_check,
    job_in_queue_check,
    run_all,
)
from .celigo_single_image.celigo_single_image_core import (
    CeligoSingleImageCore,
)

__all__ = "CeligoSingleImageCore"
