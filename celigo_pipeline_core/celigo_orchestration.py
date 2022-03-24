from multiprocessing.connection import wait
import os
from pathlib import Path
import subprocess
import time


from .celigo_single_image import CeligoSingleImageCore


def run_all(raw_image_path):

    image = CeligoSingleImageCore(raw_image_path)

    job_ID, output_file = image.downsample()
    job_complete_check(job_ID, output_file,'downsample')
    job_ID, output_file = image.run_ilastik()
    job_complete_check(job_ID, output_file,'ilastik')
    job_ID, output_dir = image.run_cellprofiler()
    job_complete_check(job_ID, output_dir,'cell profiler')
    # Upload

    print("Complete")


def job_complete_check(job_ID, endfile,name):
    job_status = "waiting"

    while (not endfile.exists()) and job_status != "complete":
        time.sleep(3)
        count = 0
        if (not (job_in_queue_check(job_ID))) and (job_status == "waiting"):
            job_status = "waiting"  # could change to pass
            print('waiting')

        elif job_in_queue_check(job_ID):
            job_status = "running"
            print(f"Job: {job_ID} {name} is running")

        elif not endfile.exists() and count < 200: # add and max runtime hasnt been reached 
            job_status = "failed"
            print(f"Job: {job_ID} {name} has failed!")
            break
        
        elif endfile.exists(): 
            job_status = 'complete'
            print(f"Job: {job_ID} {name} is complete!")

        count = count + 1

def job_in_queue_check(job_ID):
    output = subprocess.run(
        ["squeue", "-j", f"{job_ID}"], check=True, capture_output=True
    )
    return output.stdout.decode("utf-8").count("\n") >= 2
