import os
import collections
from abc import ABC

WatchEvent = collections.namedtuple('WatchEvent', ['index', 'path', 'data', 'fullname'])

class AbstractWatchDir(ABC):
    def __init__(self):
        pass

    def add_watch(self, path, recursive = False, data = None):
        """
            Adds a directory to watch

        Args:
            path: The path to watch.
            recursive: if true, notify any change on subdirectories
            data: optional data associated to the watch. This object will be
            returned by the read() functions when something changes on the
            directory.
        """

    def rm_watch(self, value):
        """Removes a watched directory

        Args:
            value (int): The index of the descriptor to remove
            value (str): The path to remove 
        """

    def read(self, timeout=None, read_delay=None):
        """Check if there is any changes on any watched directory (added with add_watch() function).

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
                tuple: (path watched, data associated with path)
            
            if nothing changes after timeout:
                None

            or raise an error

        url: https://docs.microsoft.com/pt-br/windows/desktop/api/winuser/nf-winuser-msgwaitformultipleobjects
            """

    def close(self):
        """
        Removes and closes nicely all watched directories
        """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


if os.name == 'nt':
    #from .watcher_win32_FindFirstChangeNotification import WatchDir
    from .watcher_win32 import WatchDir
else:
    from .watcher_posix import WatchDir


__all__ = ['WatchDir', 'WatchEvent']
