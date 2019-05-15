# font: http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
import os
import time
# pip install pywin32
import win32file
import win32con
import threading
import queue
from . import AbstractWatchDir, WatchEvent

def log(text):
    print("DEBUG: %s" % text)

ACTIONS = {
  1 : "Created",
  2 : "Deleted",
  3 : "Updated",
  4 : "Renamed to something",
  5 : "Renamed from something"
}

class Watcher(threading.Thread):
    def __init__ (self, path_to_watch, recursive, data, results_queue, **kwds):
        threading.Thread.__init__ (self, **kwds)
        self.setDaemon(1)
        self.path_to_watch = path_to_watch
        self.recursive = recursive
        self.data = data
        
        self.results_queue = results_queue

        FILE_LIST_DIRECTORY = 0x0001
        self.handle = win32file.CreateFile (
            path_to_watch,
            FILE_LIST_DIRECTORY,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_BACKUP_SEMANTICS,
            None
        )
        self.start()

    def run (self):
        for result in self.watch_path():
            self.results_queue.put(result)

    def watch_path(self):
        while 1:
            results = win32file.ReadDirectoryChangesW (
                self.handle,
                1024,
                self.recursive,
                win32con.FILE_NOTIFY_CHANGE_FILE_NAME | 
                    win32con.FILE_NOTIFY_CHANGE_DIR_NAME #|
                    #win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                    #win32con.FILE_NOTIFY_CHANGE_SIZE |
                    #win32con.FILE_NOTIFY_CHANGE_LAST_WRITE #|
                    #win32con.FILE_NOTIFY_CHANGE_SECURITY
                    , 
                None,
                None
            )
            for action, file in results:
                full_filename = os.path.join(self.path_to_watch, file)
                yield WatchEvent(
                          index=self.handle,
                          path=self.path_to_watch,
                          data=self.data,
                          fullname=full_filename)

    def ___del__():
        self.handle.Close()
        
class WatchDir(AbstractWatchDir):
    def __init__(self):
        self.files_changed = queue.Queue()
        self.watchers = []
        self.readQueue = {}
        pass

    def add_watch(self, path, recursive = False, data = None):
        #log("WatchDir: add_watch(%s, %r, %r)" % (path, recursive, data))
        self.watchers.append(Watcher(path, recursive, data, self.files_changed))
        return len(self.watchers)

    def rm_watch(self, id):
        del self.watchers[id]
        return True
        
    def readAll(self, timeout=None, read_delay=None):
        """

        Args:
            timeout (int): The time in milliseconds to wait for events if
                there are none. If `negative or `None``, block until there are
                events.

            read_delay (int): The time in milliseconds to wait after the first
                event arrives before reading the buffer. This allows further
                events to accumulate before reading, which allows the kernel
                to consolidate like events and can enhance performance when
                there are many similar events.

        Returns:
            if some file changes on some path being watched:
                Event: Path to watch, data associated with path, Full Filename, File Type (File or Folder), action on file)

            if nothing changes after timeout:
            None
            """
        if read_delay is not None:
            # Wait for more events to accumulate:
            time.sleep(read_delay/1000.0)

        if timeout is None:
            timeout = False
        else:
            timeout = timeout / 1000.0
            
        try:
            res = self.files_changed.get(True, timeout)
            return res
        except queue.Empty:
            return None


    def read(self, timeout=None, read_delay=None):
        change = self.readAll(timeout, read_delay)
        while change is not None:
            self.readQueue[change.fullname] = change
            change = self.readAll(0, None)

        keys = list(self.readQueue.keys())
        if len(keys) > 0:
            res = self.readQueue[keys[0]]
            del self.readQueue[keys[0]]
            return res
        else:
            return None
