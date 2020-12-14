import time
from shutil import rmtree


def remove_tree(path, retries=3, sleep=0.1):
    for i in range(retries):
        try:
            rmtree(path, False)
        except WindowsError:
            time.sleep(sleep)
        else:
            break
