import argparse
import logging
import sys
import traceback

from celigo_pipeline_core.celigo_orchestration import (
    run_all,
)

log = logging.getLogger()


class Args(argparse.Namespace):
    def __init__(self):
        super().__init__()
        self.debug = False
        self.image_path = str()
        self.postgres_password = str()
        self.__parse()

    def __parse(self):
        p = argparse.ArgumentParser(
            prog="CeligoPipeline",
            description="generates Cell Profiler Output metrics from Celigo Images ",
        )

        p.add_argument(
            "--image_path",
            dest="image_path",
            type=str,
            help="Image file location on local computer (Image for Processing)",
            required=True,
        )

        p.add_argument(
            "--postgres_password",
            dest="postgres_password",
            type=str,
            help="password for accessing postgres password for metric upload.",
            required=True,
        )

        p.add_argument(
            "--debug",
            help="Enable debug mode",
            default=False,
            required=False,
            action="store_true",
        )

        # make array with options
        p.add_argument(
            "--env",
            type=str,
            help="Environment that data will be stored to('prod, 'stg', default is 'stg')",
            default="stg",
            required=False,
        )

        p.parse_args(namespace=self)

    ###############################################################################


def main():
    args = Args()
    debug = args.debug

    try:
        run_all(
            raw_image_path=args.image_path, postgres_password=args.postgres_password
        )

    except Exception as e:
        log.error("=============================================")
        if debug:
            log.error("\n\n" + traceback.format_exc())
            log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == "__main__":
    main()
