from multiprocessing.connection import wait
import os
from pathlib import Path
import subprocess

from celigo_single_image_core import CeligoSingleImageCore


def run_all(raw_image_path):

    image = CeligoSingleImageCore(raw_image_path)

    '''
    Job_status = waiting

    While endfile ! Exist & job ! in queue & job_status != ‘waiting’ :
        
        If job not in queue & Status != ‘running’:
            Status = waiting
        Elif job in queue
            Status = running
        Elif file ! exist
            Status = Job 
        else 
            status = 'complete'
    Rerun or Break	
    '''

    

    image.downsample()

    image.run_ilastik()

    image.run_cellprofiler()

    # Upload

    print("Complete")

    def run_job(endfile,job_ID):
        job_status = 'waiting'

        while (not os.path.exists(endfile)) and job_status != 'complete':
            
            if  not (job_in_queue_check(job_ID)) and job_status is 'waiting':
                job_status = 'waiting' # could change to pass
            elif (job_in_queue_check(job_ID)):
                job_status = 'running'
            elif not os.path.exists(endfile):
                job_status = 'failed'
                break
            else:
                job_status = 'complete'

        if job_status is 'failed':
            x = 0
    def job_in_queue_check(job_ID):
        subprocess.run(["squeue", "-j", f"{job_ID}"])
        
