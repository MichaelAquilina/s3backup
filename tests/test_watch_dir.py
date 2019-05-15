from watchdir import *
import os

import threading
import time
import shutil
PREFIX="_tmp"
DIR_1=os.path.join(PREFIX, "1")
DIR_1_A=os.path.join(DIR_1, "a")
DIR_2=os.path.join(PREFIX, "2")
DIR_2_A=os.path.join(DIR_2, "a")

FILE_1_X=os.path.join(DIR_1, "x.txt")
FILE_1A_Y=os.path.join(DIR_1_A, "y.txt")
DIR1_B=os.path.join(DIR_1, "b")

FILE_2_X=os.path.join(DIR_2, "x.txt")
FILE_2A_Y=os.path.join(DIR_2_A, "y.txt") # should not fire a notification
DIR2_B=os.path.join(DIR_2, "b")

def log(msg):
   print(msg)
   
def write_file(path, text):
    with open(path, "w+") as fp:
        fp.write(text)

def worker():
    DELAY=2
    global FILE_1_X
    global FILE_1A_Y
    global DIR_1_B
    global FILE_2_X
    global FILE_2A_Y
    global DIR_2_B
    log("worker: Started")
    time.sleep(DELAY)
    log("worker: FILE1_X")
    write_file(FILE_1_X, "File 1 X")
    time.sleep(DELAY)
    log("worker: FILE1A_Y")
    write_file(FILE_1A_Y, "File 1 Y")
    time.sleep(DELAY)
    log("worker: DIR1_B")
    os.mkdir(DIR1_B)

    time.sleep(DELAY)
    log("worker: FILE2_X")
    write_file(FILE_2_X, "File 2 X")
    time.sleep(DELAY)
    log("worker: FILE2A_Y")
    write_file(FILE_2A_Y, "File 2 Y")
    time.sleep(DELAY)
    log("worker: DIR2_B")
    os.mkdir(DIR2_B)
    log("Ended worker")

class TestWatchDir():
    def test_watch_dir(self):
        global DIR1
        global DIR1_A
        global DIR2
        global DIR2_A
        log("Making dirs")
        try:
            shutil.rmtree(PREFIX) 
        except:
            pass
        try:
            os.mkdir(PREFIX)
            os.mkdir(DIR_1)
            os.mkdir(DIR_2)
            os.mkdir(DIR_1_A)
            os.mkdir(DIR_2_A)
        except:
            pass

        log("Configuring WatchDir")
        wd = WatchDir()
        # dir 1 is watched on subdirectories
        wd.add_watch("_tmp\\1", True, "data 1")
        # dir 2 is not
        wd.add_watch("_tmp\\2", False, "data 2")

        log("Starting Threads")
        t = threading.Thread(target=worker)
        t.start()

        log("Loop")
        test_result = []
        i = 0
        while i < 40:
            log("Step %d" % i)
            res = wd.read(timeout=500, read_delay=100)
            log(res)
            if res is not None:
                test_result.append(res)
                log("result:")
                log(test_result)

            i = i + 1


        log("Test result:")
        log(test_result)
        assert(len(test_result) == 5)
        assert(test_result[0].data == 'data 1')
        assert(test_result[1].data == 'data 1')
        assert(test_result[2].data == 'data 1')
        assert(test_result[3].data == 'data 2')
        assert(test_result[4].data == 'data 2')
            
        try:
            shutil.rmtree(PREFIX) 
        except:
            pass
        
if __name__ == '__main__':
    me = TestWatchDir()
    me.test_watch_dir()
