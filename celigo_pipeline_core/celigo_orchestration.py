from multiprocessing.connection import wait
import os
from pathlib import Path
import subprocess

from celigo_single_image.celigo_single_image_core import CeligoSingleImageCore


def run_all(raw_image_path):

    image = CeligoSingleImageCore(raw_image_path)

    job_ID, output_file = image.downsample()
    job_complete_check(job_ID, output_file)
    job_ID, output_file = image.run_ilastik()
    job_complete_check(job_ID, output_file)
    job_ID, output_dir = image.run_cellprofiler()
    job_complete_check(job_ID, output_dir)
    # Upload

    print("Complete")


def job_complete_check(job_ID, endfile):
    job_status = "waiting"

    while (not endfile.exists()) and job_status != "complete":

        if (not (job_in_queue_check(job_ID))) and (job_status == "waiting"):
            job_status = "waiting"  # could change to pass
        elif job_in_queue_check(job_ID):
            job_status = "running"
        elif not endfile.exists():
            job_status = "failed"
            break
        else:
            job_status = "complete"
            print(f"job {job_ID} is is complete!")

    if job_status == "failed":
        print(f"job {job_ID} is Failed")


def job_in_queue_check(job_ID):
    output = subprocess.run(
        ["squeue", "-j", f"{job_ID}"], check=True, capture_output=True
    )
    return output.stdout.decode("utf-8").count("\n") >= 2
