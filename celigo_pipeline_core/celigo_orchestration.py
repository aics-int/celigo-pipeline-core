import pathlib
import shutil
import subprocess
import time
import pathlib
import os

from .celigo_single_image import (
    CeligoSingleImageCore,
)


def run_all(raw_image_path: pathlib.Path):
    upload_location = pathlib.Path('/allen/aics/microscopy/PRODUCTION/Celigo_Metric_Output')
    image = CeligoSingleImageCore(raw_image_path)

    job_ID, output_file = image.downsample()
    job_complete_check(job_ID, output_file, "downsample")
    job_ID, output_file = image.run_ilastik()
    job_complete_check(job_ID, output_file, "ilastik")
    job_ID, output_file = image.run_cellprofiler()
    job_complete_check(job_ID, output_file, "cell profiler")
    # job_ID, output_dir = image.upload_metrics()
    # job_complete_check(job_ID, output_dir, "cell profiler")
    shutil.copytree(output_file.parent,upload_location)
    os.rename(upload_location / "cell_profiler_outputs", upload_location / output_file.with_suffix("").name)
    # Upload raw image with low priority
    image.cleanup()
    print("Complete")


# This function runs in between bash script calls to determine when the correct files are output
# and when to go onto the next process.
def job_complete_check(
    job_ID: int,
    endfile: pathlib.Path,
    name: str,
):

    job_status = "waiting"  # Status code for bash script process
    count = 0  # number of time through loop each is about 3 sec. This is to determine when to break out and say the process failed

    # Loop goes while the output file isnt there and the job isnt complete
    while (not endfile.exists()) and job_status != "complete":
        time.sleep(
            3
        )  # wait in between each loop to not get incorrect codes or too much printed info to terminal

        # initial check to see if job was ever added to queue. Sometimes this can take a bit
        if (not (job_in_queue_check(job_ID))) and (job_status == "waiting"):
            job_status = "waiting"
            print("waiting")

        # If the job is in the queue (running) prints "Job; <Number> <Name> is running"
        elif job_in_queue_check(job_ID):
            job_status = "running"
            print(f"Job: {job_ID} {name} is running")

            """ 
                Once job is in the queue the loop will continue printing running until 
                the job is no longer in the queue. Then the next logic statements come
                into play to determine if the run was sucessful 

            """
        # This logic is only reached if the process ran and is no longer in the queue
        # Counts to 600 to wait and see if the output file gets created. If it doesnt then
        # prints that the job has failed and breaks out of the loop.
        elif not endfile.exists() and count > 200:
            job_status = "failed"
            print(f"Job: {job_ID} {name} has failed!")
            break

        # The final statement confirming if the process was sucessful.
        elif endfile.exists():
            job_status = "complete"
            print(f"Job: {job_ID} {name} is complete!")

        count = count + 1  # Internal clock adding one to times through while loop.


# Function that checks if a current job ID is in the squeue. Returns True if it is and False if it isnt.
def job_in_queue_check(job_ID: int):

    output = subprocess.run(
        ["squeue", "-j", f"{job_ID}"], check=True, capture_output=True
    )

    # The output of subprocess is an array turned into a string so in order to
    # count the number of entries we count the frequency of "\n" to show if the
    # array was not empty, indicating the job is in the queue.
    return output.stdout.decode("utf-8").count("\n") >= 2
