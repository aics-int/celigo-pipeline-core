import os
import pathlib
import shutil
import subprocess
import time
from pipeline_uploaders import CeligoUploader 

from .celigo_single_image import (
    CeligoSingleImageCore,
)


def run_all(
    raw_image_path: pathlib.Path,
    upload_location: pathlib.Path = "/allen/aics/microscopy/PRODUCTION/Celigo_Metric_Output",
):
    """Process Celigo Images from `raw_image_path`. Submits jobs for Image Downsampling,
    Image Ilastik Processing, and Image Celigo Processing. After job completion,
    Image Metrics are uploaded to an external database.

    Parameters
    ----------
    raw_image_path : pathlib.Path
        Path must poinntn a .Tiff image produced by the Celigo camera. Path must be accessable
        from SLURM (ISILON[OK])

    Keyword Arguments
    -----------------
    upload_location : Optional[pathlib.Path]
        You have the option to specify an output directory for post processing metrics.
        Otherwise metrics are saved to /allen/aics/microscopy/PRODUCTION/Celigo_Metric_Output
    """

    image = CeligoSingleImageCore(raw_image_path)

    job_ID, output_file = image.downsample()
    job_complete_check(job_ID, output_file, "downsample")
    job_ID, output_file = image.run_ilastik()
    job_complete_check(job_ID, output_file, "ilastik")
    job_ID, output_file = image.run_cellprofiler()
    job_complete_check(job_ID, output_file, "cell profiler")
    image.upload_metrics()
    image.cleanup()
    
    # shutil.copytree(output_file.parent, upload_location / output_file.with_suffix("").name)

    # Upload This might need to be called on a diffrent call if they are running in sucession. 
    # Consider returning celigo_img appending to a list and calling upload from there.

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
        Job has failed, the specified `endfile ` was not created within the specified time
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

    output = subprocess.run(
        ["squeue", "-j", f"{job_ID}"], check=True, capture_output=True
    )

    # The output of subprocess is an array turned into a string so in order to
    # count the number of entries we count the frequency of "\n" to show if the
    # array was not empty, indicating the job is in the queue.

    return output.stdout.decode("utf-8").count("\n") >= 2
