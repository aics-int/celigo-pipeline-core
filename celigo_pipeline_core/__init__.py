__author__ = "AICS"

# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "2.1.0"


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
from .notifcations import (
    send_slack_notification_on_failure,
    slack_day_report,
    get_channel_emails,
)
from .postgres_db_functions import (
    add_FMS_IDs_to_SQL_table,
    add_to_table,
)

__all__ = "CeligoSingleImageCore"
