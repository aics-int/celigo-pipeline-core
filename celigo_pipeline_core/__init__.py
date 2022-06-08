__author__ = "AICS"

# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "2.3.0"


def get_module_version():
    return __version__


from .celigo_orchestration import (
    job_complete_check,
    job_in_queue_check,
    run_all,
    run_all_dir,
)
from .celigo_single_image.celigo_image import (
    CeligoImage,
)
from .celigo_single_image.celigo_single_image_core import (
    CeligoSingleImageCore,
)
from .celigo_single_image.celigo_six_well_core import (
    CeligoSixWellCore,
)
from .notifcations import (
    get_channel_emails,
    send_slack_notification_on_failure,
    slack_day_report,
)
from .postgres_db_functions import (
    add_FMS_IDs_to_SQL_table,
    add_to_table,
)

__all__ = "CeligoSingleImageCore"
