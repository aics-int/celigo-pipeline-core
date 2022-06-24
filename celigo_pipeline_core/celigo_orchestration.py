from datetime import date, datetime
import multiprocessing
import os
import pathlib
from pathlib import Path
import pwd
import shutil
import subprocess
import time
from typing import List

from aics_pipeline_uploaders import CeligoUploader
from dotenv import load_dotenv
import pandas as pd
import psycopg2

from .celigo_single_image import (
    CeligoImage,
    CeligoSingleImageCore,
    CeligoSixWellCore,
)
from .notifcations import (
    send_slack_notification_on_failure,
)
from .postgres_db_functions import (
    add_FMS_IDs_to_SQL_table,
    add_to_table,
)


def run_all(
    raw_image_path: str,
):
    """Process Celigo Images from `raw_image_path`. Submits jobs for Image Downsampling,
    Image Ilastik Processing, and Image Celigo Processing. After job completion,
    Image Metrics are uploaded to an external database.

    Parameters
    ----------
    raw_image_path : pathlib.Path
        Path must point to a .Tiff image produced by the Celigo camera. Path must be accessable
        from SLURM (ISILON[OK])

    postgres_password : str
        Password used to access Microscopy DB. (Contact Brian Whitney, Aditya Nath, Tyler Foster)

    """
    # Check if path is real
    if not os.path.exists(raw_image_path):
        raise FileNotFoundError(f"{raw_image_path} does not exist!")

    env = f"/home/{pwd.getpwuid(os.getuid())[0]}/.env"
    load_dotenv(env)
    env_vars = [
        os.getenv("MICROSCOPY_DB"),
        os.getenv("MICROSCOPY_DB_USER"),
        os.getenv("MICROSCOPY_DB_PASSWORD"),
        os.getenv("MICROSCOPY_DB_HOST"),
        os.getenv("MICROSCOPY_DB_PORT"),
        os.getenv("CELIGO_SLACK_TOKEN"),
        os.getenv("CELIGO_METRICS_DB"),
        os.getenv("CELIGO_STATUS_DB"),
        os.getenv("CELIGO_CHANNEL_NAME"),
    ]

    if any(env_vars) == "None":
        raise EnvironmentError(
            "Environment variables were not loaded correctly. Try adding 'load_dotenv(find_dotenv())' to your script"
        )

    if os.path.getsize(raw_image_path) > 100000000:
        image = CeligoSixWellCore(raw_image_path)  # type: CeligoImage
        table = str(os.getenv("CELIGO_6_WELL_METRICS_DB"))
        print("6 Well")
    else:
        image = CeligoSingleImageCore(raw_image_path)
        table = str(os.getenv("CELIGO_METRICS_DB"))
        print("96 Well")

    raw_image = Path(raw_image_path)
    upload_location = raw_image.parent
    status = "Running"

    try:
        conn = psycopg2.connect(
            database=os.getenv("MICROSCOPY_DB"),
            user=os.getenv("MICROSCOPY_DB_USER"),
            password=os.getenv("MICROSCOPY_DB_PASSWORD"),
            host=os.getenv("MICROSCOPY_DB_HOST"),
            port=os.getenv("MICROSCOPY_DB_PORT"),
        )
    except Exception as e:
        print("Connection Error: " + str(e))

    status = "Running"

    try:
        job_ID, downsample_output_file_path = image.downsample()
        job_complete_check(job_ID, [downsample_output_file_path], "downsample")
        job_ID, ilastik_output_file_path = image.run_ilastik()
        job_complete_check(job_ID, [ilastik_output_file_path], "ilastik")
        job_ID, cellprofiler_output_file_paths = image.run_cellprofiler()
        job_complete_check(
            job_ID, cellprofiler_output_file_paths, "cell profiler"
        )  # add to status loop return Status

        index = image.upload_metrics(conn, table)

        # Copy files off isilon for off cluster upload
        shutil.copyfile(
            ilastik_output_file_path,
            upload_location / ilastik_output_file_path.name,
        )
        shutil.copyfile(
            cellprofiler_output_file_paths[0],
            upload_location / cellprofiler_output_file_paths[0].name,
        )

        # Cleans temporary files from slurm node
        image.cleanup()

        # Upload IMG, Probababilities, Outlines to FMS
        print("uploading")

        fms_IDs = upload(
            raw_image_path=Path(raw_image_path),
            probabilities_image_path=upload_location / ilastik_output_file_path.name,
            outlines_image_path=upload_location
            / cellprofiler_output_file_paths[0].name,
        )

        print("Upload Complete")
        # Add FMS ID's from uploaded files to postgres database
        add_FMS_IDs_to_SQL_table(
            metadata=fms_IDs,
            conn=conn,
            index=index,
            table=table,
        )

        status = "Complete"  # this wont be needed if we check after each task

    except Exception as e:
        print("is broke")
        error, status = e, "Failed"
        send_slack_notification_on_failure(file_name=raw_image.name, error=str(error))
        image.cleanup()  # This needs an if exists
        print("Error: " + str(error))

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    submission = {
        "File Name": [raw_image.name],
        "Status": [status],
        "Date": [str(date.today())],
        "Time": [current_time],
    }

    if status == "Complete":
        submission["FMS ID"] = [fms_IDs["RawCeligoFMSId"]]
    if status == "Failed":
        submission["Error Code"] = [str(error)]

    row_data = pd.DataFrame.from_dict(submission)
    add_to_table(metadata=row_data, conn=conn, table=str(os.getenv("CELIGO_STATUS_DB")))

    print(status)


def job_complete_check(
    job_ID: int,
    filelist: List[pathlib.Path],
    name: str = "",
):
    """Provides a tool to check job status of SLURM Job ID. Job Status is Dictated by the following
    1) Status : waiting
        job has not yet entered the SLURM queue. This could indicate heavy traffic or that
        the job was submitted incorrectly and will not execute.
    2) Status : running
        Job has been sucessfully submitted to SLURM and is currently in the queue. This is not
        an indicator of sucess, only that the given job was submitted
    3) Status : failed
        Job has failed, the specified `endfile` was not created within the specified time
        criteria. Most likely after this time it will never complete.
    4) Status : complete
        Job has completed! and it is ok to use the endfile locationn for further processing

    Parameters
    ----------
    job_ID: int
        The given job ID from a bash submission to SLURM. This is used to check SLURM's
        running queue and determine when the job is no longer in queue (Either Failed or Sucess)
    endfile: pathlib.Path
        `endfile` is our sucess indicator. After 'job_ID' is no longer in SLURM's queue, we confirm the
        process was sucessful with the existence of `endfile`. If the file does not exist after an
        extended time the job is marked as failed

    Keyword Arguments
    -----------------
    name : Optional[str]
        Name or Type of job submitted to SLURM for tracking / monitering purposes
    """

    job_status = "waiting"  # Status Code
    count = 0  # Runtime Counter

    # Main Logic Loop: waiting for file to exist or maximum wait-time reached.
    while (not all([os.path.isfile(f) for f in filelist])) and (
        job_status != "complete"
    ):

        # Wait between checks
        time.sleep(3)

        # Initial check to see if job was ever added to queue, Sometimes this can take a bit.
        if (not (job_in_queue_check(job_ID))) and (job_status == "waiting"):
            job_status = "waiting"
            print("waiting")

        # If the job is in the queue (running) prints "Job; <Number> <Name> is running"
        elif job_in_queue_check(job_ID):
            job_status = "running"
            print(f"Job: {job_ID} {name} is running")

            # Once job is in the queue the loop will continue printing running until
            # the job is no longer in the queue. Then the next logic statements come
            # into play to determine if the run was sucessful

        elif not all([os.path.isfile(f) for f in filelist]) and count > 1000:
            # This logic is only reached if the process ran and is no longer in the queue
            # Counts to 600 to wait and see if the output file gets created. If it doesnt then
            # prints that the job has failed and breaks out of the loop.

            job_status = "failed"
            print(f"Job: {job_ID} {name} has failed!")
            break

        # The final statement confirming if the process was sucessful.
        elif all([os.path.isfile(f) for f in filelist]):
            job_status = "complete"
            print(f"Job: {job_ID} {name} is complete!")

        count = count + 1  # Runtime Increase


# Function that checks if a current job ID is in the squeue. Returns True if it is and False if it isnt.
def job_in_queue_check(job_ID: int):

    """Checks if a given `job_ID` is in SLURM queue.

    Parameters
    ----------
    job_ID: int
        The given job ID from a bash submission to SLURM.
    """
    output = subprocess.run(
        ["squeue", "-j", f"{job_ID}"], check=True, capture_output=True
    )

    # The output of subprocess is an array turned into a string so in order to
    # count the number of entries we count the frequency of "\n" to show if the
    # array was not empty, indicating the job is in the queue.

    return output.stdout.decode("utf-8").count("\n") >= 2


def upload(
    raw_image_path: pathlib.Path,
    probabilities_image_path: pathlib.Path,
    outlines_image_path: pathlib.Path,
) -> dict:

    """Provides wrapped process for FMS upload. Throughout the Celigo pipeline there are a few files
    We want to preserve in FMS.

    1) Original Image

    2) Ilastik Probabilities

    3) Cellprofiler Outlines

    Parameters
    ----------
    raw_image_path: pathlib.Path
        Path to raw image (TIFF). Set internally through `run_all`. Metadata is Created from the file
        name through `CeligoUploader`
    probabilities_image_path: pathlib.Path
        Path to image probability map (TIFF). Set internally through `run_all`. Metadata is Created from the file
        name through `CeligoUploader`
    outlines_image_path: pathlib.Path
        Path to cellprofiler output (PNG). Set internally through `run_all`. Metadata is Created from the file
        name through `CeligoUploader`

    Returns
    -------
    metadata: dictionary of FMS IDS
    """

    raw_file_type = "Tiff Image"
    probabilities_file_type = "Probability Map"
    outlines_file_type = "Outline PNG"

    metadata = {}

    metadata["RawCeligoFMSId"] = CeligoUploader(raw_image_path, raw_file_type).upload()
    print(metadata["RawCeligoFMSId"])

    metadata["ProbabilitiesMapFMSId"] = CeligoUploader(
        probabilities_image_path, probabilities_file_type
    ).upload()
    print(metadata["ProbabilitiesMapFMSId"])
    metadata["OutlinesFMSId"] = CeligoUploader(
        outlines_image_path, outlines_file_type
    ).upload()
    print(metadata["OutlinesFMSId"])
    # os.remove(probabilities_image_path)  # this should be in a try
    # os.remove(outlines_image_path)
    return metadata


def split(list_a, chunk_size):
    for i in range(0, len(list_a), chunk_size):
        yield list_a[i : i + chunk_size]


def run_all_dir(dir_path: str, chunk_size: int = 30):
    processes = []
    start = time.perf_counter()

    for subdir, _, files in os.walk(dir_path):
        for files in list(split(files, chunk_size)):
            for file in files:
                if "350000" in file and "escale" not in file:
                    path = f"{subdir}/{file}"
                    p = multiprocessing.Process(target=run_all, args=[path])
                    p.start()
                    processes.append(p)
                else:
                    continue

            for process in processes:
                process.join()

    finish = time.perf_counter()

    print(f"Finished in {round(finish-start,2)} second(s)")
