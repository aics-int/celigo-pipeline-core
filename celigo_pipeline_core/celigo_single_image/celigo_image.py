import shutil


class CeligoImage:
    def __init__(self):
        self.type = CeligoImage

    def cleanup(self):
        """Removes created working directory from SLURM so
        that the work space does not become overencumbered.
        """
        shutil.rmtree(self.working_dir)

    def downsample(self):
        return ["None", "None"]

    def run_ilastik(self):
        return ["None", "None"]

    def run_cellprofiler(self):
        return ["None", ["None"]]

    def upload_metrics(self, conn, table: str) -> str:
        return "None"
