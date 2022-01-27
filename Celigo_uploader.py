from aicsfiles import FileManagementSystem

class celigo_uploader:

    def __init__(self,file_type,path):
        self.path = path
        self.file_type = file_type
        file_name = open(self.path).name.split('\\')[-1]

        raw_metadata = file_name.split("_")

        plate_barcode = raw_metadata[0]

        ts = raw_metadata[2].split('-')
        scan_date = ts[0] + '-'+ ts[1] + '-'+ ts[2]
        scan_time = ts[4] + '-'+ ts[5] + '-'+ ts[6]

        row = raw_metadata[4][0]
        col = raw_metadata[4][1:]
        
        self.metadata = {
            "microsocpy": {
                "plate_barcode": [plate_barcode],  # an existing fms file_id
                "celigo": {
                    "scan_time": [scan_time],
                    "scan_date": [scan_date],
                    "row": [row],
                    "coll": [col],
                },
            },
        }

    def upload(self):  
        fms = FileManagementSystem()
        while True:
            try:
                fms.upload_file(self.path, file_type = self.file_type, metadata = self.metadata)
                break
            except OSError:
                print("File Not Uploaded")
            except ValueError:
                print("File Not Uploaded")
            except BaseException:
                print("File Not Uploaded")

