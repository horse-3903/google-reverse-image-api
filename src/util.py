import os
import tempfile
from tempfile import _TemporaryFileWrapper

def create_tmp() -> _TemporaryFileWrapper:
    tmp_files = os.listdir("temp/")
    active_file = None

    # creating tmp file
    if not tmp_files:
        print("INFO: Creating Temporary File")
        active_file = tempfile.NamedTemporaryFile(mode="w+", dir="temp/", delete=False)
    
    # restoring tmp file
    else:
        print("INFO: Restoring Temporary File")

        with open("temp/"+tmp_files[0], "r") as f:
            tmp_data = f.read()

        active_file = tempfile.NamedTemporaryFile(mode="w+", dir="temp/", delete=False)

        try:
            active_file.truncate()
            active_file.seek(0)
            active_file.write(tmp_data)
            active_file.seek(0)
        finally:
            os.remove("temp/"+tmp_files[0])
    
    return active_file