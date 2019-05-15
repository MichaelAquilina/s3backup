# font: http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
import os
import time
from inotify_simple import INotify
from inotify_simple import flags
from . import AbstractWatchDir

class WatchDir(AbstractWatchDir):

    def __init__(self):
        self.inotify = INotify()
        self._handles = []
        self._paths = []
        self._datas = []
        pass

    def add_watch(self, path, recursive = False, data = None):
        self.add_watch(path, recursive, data)

    def _add_watch(self, path, recursive = False, data = None):
        watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY

        handle = self.inotify.add_watch(path, watch_flags)
        self._handles.append(handle)
        self._paths.append(path)
        self._data.append(data)
        if recursive:
            for item in scandir(path):
                if item.is_dir():
                    handle = self._add_watch(item.path, True, watch_flags)
                    self._handles.append(handle)
                    self._paths.append(item.path)
                    self._data.append(data)
        return handle

    def rm_watch(self, value):
        if type(value) is not int:
            index = self._paths.index(xd) 
        else:
            index = value

        self.inotify.rm_watch(self._handles[index])
        del self._handles[index]
        del self._paths[index]
        del self._datas[index]

    def read(self, timeout=None, read_delay=None):
        res = self.inotify.read(timeout, read_delay)

        if res is []:
            return None
        
        wd = res.wd
        name = res.name
        index = self._paths.index(xd) 

        return WatchEvent(index=index,
                path=self._paths[index], 
                data=self._data[index], 
                fullname=name)

