# font: http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
import os
import time
# pip install pywin32
import win32api
import win32file
import win32event
import win32con
from . import AbstractWatchDir

class WatchDir(AbstractWatchDir):

    def __init__(self):
        self._handles = []
        self._paths = []
        self._datas = []
        pass

    def add_watch(self, path, recursive = False, data = None):
        #
        # FindFirstChangeNotification sets up a handle for watching
        #  file changes. The first parameter is the path to be
        #  watched; the second is a boolean indicating whether the
        #  directories underneath the one specified are to be watched;
        #  the third is a list of flags as to what kind of changes to
        #  watch for. 
        #  url: https://docs.microsoft.com/en-us/windows/desktop/api/fileapi/nf-fileapi-findnextchangenotification
        res = win32file.FindFirstChangeNotification (
               path,
               win32con.TRUE if recursive == True else win32con.FALSE,
               win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
               win32con.FILE_NOTIFY_CHANGE_DIR_NAME #|
               #win32con.FILE_NOTIFY_CHANGE_SIZE | # was creating "ghosts"
               #win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
            )

        self._handles.append(res)
        self._paths.append(path)
        self._datas.append(data)

    def rm_watch(self, value):
        if type(value) is not int:
            index = self._paths.index(value) 
        else:
            index = value

        res = win32file.FindCloseChangeNotification(self._handles[index])
        if res == 0:
            raise RuntimeError("FindCloseChangeNotification returned error 0x%X"% win32api.GetLastError() )

        del self._handles[index]
        del self._paths[index]
        del self._datas[index]

    def read(self, timeout=None, read_delay=None):
        if read_delay is not None:
            # Wait for more events to accumulate:
            time.sleep(read_delay/1000.0)

        if timeout is None or timeout < 0:
            timeout = win32con.INFINITE

        result = win32event.WaitForMultipleObjects (self._handles, False, timeout)
        if result >= win32con.WAIT_OBJECT_0 and result <= win32con.WAIT_OBJECT_0 + len(self._handles):
            index = result - win32con.WAIT_OBJECT_0
            win32file.FindNextChangeNotification(self._handles[index])
            return WatchEvent(
                    index=index,
                    path=self._paths[index],
                    data=self._datas[index],
                    fullname=None) 
        else:
            if result == win32con.WAIT_TIMEOUT:
                return None
            else:
                raise RuntimeError("WaitForMultipleObjects returned error 0x%X"% result )
