from celigo_single_Image_core import CeligoSingleImageCore


def celigo_run_single(raw_image_path):
'''  
    WITH tempdir do the following

        img = CeligoSingleImageCore(raw_image_path, tempdir_path)
        img.downsample() 
        img.run_ilastik() # will need a wait till downsample file shows up
        img.run_cellprofiler() # will need to wait till probabilties shows up

        Copy data or upload will need to wait till cellprofiler_outputs shows up 

        confirmation of upload?

    Then on conclusion the tempdir will close
'''

def celigo_run_all:
    return None