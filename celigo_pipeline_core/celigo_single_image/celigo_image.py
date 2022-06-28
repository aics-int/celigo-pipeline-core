import abc
import shutil


class CeligoImage:
    def __init__(self):
        self.type = CeligoImage

    def cleanup(self):
        """Removes created working directory from SLURM so
        that the work space does not become overencumbered.
        """
        shutil.rmtree(self.working_dir)

    @abc.abstractmethod
    def downsample(self):
        pass

    @abc.abstractmethod
    def run_ilastik(self):
        pass

    @abc.abstractmethod
    def run_cellprofiler(self):
        pass

    @abc.abstractmethod
    def upload_metrics(self, conn, table: str) -> str:
        pass
