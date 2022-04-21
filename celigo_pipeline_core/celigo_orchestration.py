import os
import pathlib
from pathlib import Path
import shutil
import subprocess
import time

from aics_pipeline_uploaders import CeligoUploader
import psycopg2

from .celigo_single_image import (
    CeligoSingleImageCore,
)

TABLE_NAME = '"Celigo_96_Well_Data_Test_V_FOUR"'


def run_all(
    raw_image_path: str,
    postgres_password: str,
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

    image = CeligoSingleImageCore(raw_image_path)

    raw_image = Path(raw_image_path)
    upload_location = raw_image.parent

    job_ID, downsample_output_file_path = image.downsample()
    job_complete_check(job_ID, downsample_output_file_path, "downsample")
    job_ID, ilastik_output_file_path = image.run_ilastik()
    job_complete_check(job_ID, ilastik_output_file_path, "ilastik")
    job_ID, cellprofiler_output_file_path = image.run_cellprofiler()
    job_complete_check(job_ID, cellprofiler_output_file_path, "cell profiler")

    index = image.upload_metrics(
        postgres_password=postgres_password, table_name=TABLE_NAME
    )

    # Copy files off isilon for off cluster upload
    shutil.copyfile(
        ilastik_output_file_path,
        upload_location / ilastik_output_file_path.name,
    )
    shutil.copyfile(
        cellprofiler_output_file_path,
        upload_location / cellprofiler_output_file_path.name,
    )

    # Cleans temporary files from slurm node
    image.cleanup()

    # Upload IMG, Probababilities, Outlines to FMS
    fms_IDs = upload(
        raw_image_path=Path(raw_image_path),
        probabilities_image_path=upload_location / ilastik_output_file_path.name,
        outlines_image_path=upload_location / cellprofiler_output_file_path.name,
    )

    # Add FMS ID's from uploaded files to postgres database
    add_FMS_IDs_to_SQL_table(
        postgres_password=postgres_password,
        metadata=fms_IDs,
        index=index,
        table=TABLE_NAME,
    )

    print("Complete")


def job_complete_check(
    job_ID: int,
    endfile: pathlib.Path,
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
    while (not endfile.exists()) and job_status != "complete":

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

        elif not endfile.exists() and count > 200:
            # This logic is only reached if the process ran and is no longer in the queue
            # Counts to 600 to wait and see if the output file gets created. If it doesnt then
            # prints that the job has failed and breaks out of the loop.

            job_status = "failed"
            print(f"Job: {job_ID} {name} has failed!")
            break

        # The final statement confirming if the process was sucessful.
        elif endfile.exists():
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
):

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
    metadata: dictionary of upload IDS
    """
    raw_file_type = "Tiff Image"
    probabilities_file_type = "Probability Map"
    outlines_file_type = "Outline PNG"

    metadata = {}

    metadata["RawCeligoFMSId"] = CeligoUploader(raw_image_path, raw_file_type).upload()

    metadata["ProbabilitiesMapFMSId"] = CeligoUploader(
        probabilities_image_path, probabilities_file_type
    ).upload()

    metadata["OutlinesFMSId"] = CeligoUploader(
        outlines_image_path, outlines_file_type
    ).upload()

    os.remove(probabilities_image_path)
    os.remove(outlines_image_path)
    return metadata


def add_FMS_IDs_to_SQL_table(
    metadata: dict, postgres_password: str, index: str, table: str = TABLE_NAME
):
    """Provides wrapped process for Insertion of FMS IDS into Postgres Database. Throughout the Celigo pipeline there are a few files
    We want to preserve in FMS, after upload these files FMS ID's are recorded in the Microscopy DB.

    1) Original Image

    2) Ilastik Probabilities

    3) Cellprofiler Outlines

    Parameters
    ----------
    metadata: dict
        List of metadata in form [KEY] : [VALUE] to be inserted into database.
    postgres_password : str
        Password used to access Microscopy DB. (Contact Brian Whitney, Aditya Nath, Tyler Foster)
    index : str
        index defines the rows that the FMS ID's will be inserted into. In most cases this will be the Experiment ID,
        which is just the original filename.
    table: str = TABLE_NAME
        Name of table in Postgres Database intended for import. Default is chosen by DEVS given current DB status
    """

    # Connect to DB
    conn = psycopg2.connect(
        database="pg_microscopy",
        user="rw",
        password=postgres_password,
        host="pg-aics-microscopy-01.corp.alleninstitute.org",
        port="5432",
    )
    cursor = conn.cursor()

    # Submit Queries
    for key in metadata:
        query = f'UPDATE {table} SET "{key}" = %s WHERE "Experiment ID" = %s;'
        try:
            cursor.execute(query, (metadata[key], index))
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error: %s" % error)
            conn.rollback()
            cursor.close()
            return 1

    cursor.close()
