# -*- coding: utf-8 -*-

import datetime
import json
import os

from s3backup.clients import SyncAction, SyncObject


def traverse(path, ignore_files=None):
    if ignore_files is None:
        ignore_files = set()

    for item in sorted(os.listdir(path)):
        full_path = os.path.join(path, item)
        if os.path.isdir(full_path):
            for result in traverse(full_path, ignore_files):
                yield os.path.join(item, result)
        elif item not in ignore_files:
            yield item


class LocalSyncClient(object):
    def __init__(self, path):
        self.path = path
        self.index = self.load_index()

    def __repr__(self):
        return 'LocalSyncClient<{}>'.format(self.path)

    def index_path(self):
        return os.path.join(self.path, '.index')

    def put(self, key, sync_object):
        path = os.path.join(self.path, key)

        parent = os.path.dirname(path)
        if not os.path.exists(parent):
            os.makedirs(parent)

        with open(path, 'wb') as fp1:
            fp1.write(sync_object.fp.read())

        self.set_remote_timestamp(key, sync_object.timestamp)

    def get(self, key):
        path = os.path.join(self.path, key)
        if os.path.exists(path):
            fp = open(path, 'rb')
            stat = os.stat(path)
            return SyncObject(fp, stat.st_mtime)
        else:
            return None

    def delete(self, key):
        path = os.path.join(self.path, key)
        if os.path.exists(path):
            os.remove(path)
        else:
            raise IndexError('The specified key does not exist: {}'.format(key))

    def load_index(self):
        if not os.path.exists(self.index_path()):
            return {}

        with open(self.index_path(), 'r') as fp:
            data = json.load(fp)
        return data

    def update_index(self):
        keys = self.get_all_keys()
        index = {}

        for key in keys:
            index[key] = {
                'remote_timestamp': self.get_remote_timestamp(key),
                'local_timestamp': self.get_real_local_timestamp(key),
            }

        with open(self.index_path(), 'w') as fp:
            json.dump(index, fp)
        self.index = index

    def get_local_keys(self):
        return list(traverse(self.path, ignore_files={'.index'}))

    def get_real_local_timestamp(self, key):
        full_path = os.path.join(self.path, key)
        if os.path.exists(full_path):
            return os.path.getmtime(full_path)
        else:
            return None

    def get_index_keys(self):
        return self.index.keys()

    def get_index_local_timestamp(self, key):
        return self.index.get(key, {}).get('local_timestamp')

    def set_index_local_timestamp(self, key, timestamp):
        if key not in self.index:
            self.index[key] = {}
        self.index[key]['local_timestamp'] = timestamp

    def get_remote_timestamp(self, key):
        return self.index.get(key, {}).get('remote_timestamp')

    def set_remote_timestamp(self, key, timestamp):
        if key not in self.index:
            self.index[key] = {}
        self.index[key]['remote_timestamp'] = timestamp

    def get_all_keys(self):
        local_keys = self.get_local_keys()
        index_keys = self.get_index_keys()
        return list(set(local_keys) | set(index_keys))

    def get_action(self, key):
        """
        returns the action to perform on this key based on its
        state before the last sync.
        """
        index_local_timestamp = self.get_index_local_timestamp(key)
        real_local_timestamp = self.get_real_local_timestamp(key)
        remote_timestamp = self.get_remote_timestamp(key)

        if index_local_timestamp is None and real_local_timestamp:
            return SyncAction(SyncAction.UPDATE, real_local_timestamp)
        elif real_local_timestamp is None and index_local_timestamp:
            return SyncAction(SyncAction.DELETE, remote_timestamp)
        elif real_local_timestamp is None and index_local_timestamp is None and remote_timestamp:
            return SyncAction(SyncAction.DELETE, remote_timestamp)
        elif real_local_timestamp is None and index_local_timestamp is None:
            # Does not exist in this case, so no action to perform
            return SyncAction(SyncAction.NONE, None)
        elif index_local_timestamp < real_local_timestamp:
            return SyncAction(SyncAction.UPDATE, real_local_timestamp)
        elif index_local_timestamp > real_local_timestamp:
            return SyncAction(SyncAction.CONFLICT, index_local_timestamp)   # corruption?
        else:
            return SyncAction(SyncAction.NONE, remote_timestamp)
