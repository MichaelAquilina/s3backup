# -*- coding: utf-8 -*-

import enum


class StateAction(object):
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    CONFLICT = 'CONFLICT'

    def __init__(self, action, timestamp):
        self.action = action
        self.timestamp = timestamp

    def __eq__(self, other):
        if not isinstance(other, StateAction):
            return False
        return self.action == other.action and self.timestamp == other.timestamp

    def __repr__(self):
        return 'StateAction<{}, {}>'.format(self.action, self.timestamp)


class SyncAction(enum.Enum):
    DOWNLOAD = 'DOWNLOAD'
    DELETE_LOCAL = 'DELETE_LOCAL'
    DELETE_REMOTE = 'DELETE_REMOTE'
    UPLOAD = 'UPLOAD'
    CONFLICT = 'CONFLICT'


def compare_states(current, previous):
    all_keys = set(previous.keys()) | set(current.keys())
    for key in all_keys:
        in_previous = key in previous
        in_current = key in current
        previous_timestamp = previous.get(key, {}).get('local_timestamp')
        current_timestamp = current.get(key, {}).get('local_timestamp')
        if in_previous and in_current:
            if previous_timestamp == current_timestamp:
                yield key, StateAction(None, current_timestamp)
            elif previous_timestamp < current_timestamp:
                yield key, StateAction(StateAction.UPDATE, current_timestamp)
            elif previous_timestamp > current_timestamp:
                # this should only happen in the case of corruption
                yield key, StateAction(StateAction.CONFLICT, previous_timestamp)
        elif in_current and not in_previous:
            yield key, StateAction(StateAction.UPDATE, current_timestamp)
        elif in_previous and not in_current:
            yield key, StateAction(StateAction.DELETE, None)
        else:
            raise ValueError('Reached Unknown state')


def compare_actions(actions_1, actions_2):
    all_keys = set(actions_1.keys() | actions_2.keys())
    for key in all_keys:
        a1 = actions_1.get(key)
        a2 = actions_2.get(key)

        if a1 is None and a2 is None:
            continue

        elif a1 is None and a2 == StateAction.UPDATE:
            yield key, SyncAction.DOWNLOAD

        elif a1 == StateAction.UPDATE and a2 is None:
            yield key, SyncAction.UPLOAD

        elif a1 is None and a2 == StateAction.DELETE:
            yield key, SyncAction.DELETE_LOCAL

        elif a1 == StateAction.DELETE and a2 is None:
            yield key, SyncAction.DELETE_REMOTE

        else:
            yield key, SyncAction.CONFLICT


def sync(client_1, client_2):
    current = client_2.get_current_state()
    index = client_2.get_index_state()
    actions_2 = dict(compare_states(current, index))

    current = client_1.get_current_state()
    index = client_1.get_index_state()
    actions_1 = dict(compare_states(current, index))

    all_keys = set(actions_1.keys() | actions_2.keys())
    for key in all_keys:
        a1 = actions_1.get(key)
        a2 = actions_2.get(key)
        a1_action = a1.action if a1 else None
        a2_action = a2.action if a2 else None

        print(a1_action, a2_action)

        if a1_action is None and a2_action is None:
            continue

        elif a1_action is None and a2_action == StateAction.UPDATE:
            print('Updating', client_1, 'for', key)
            client_1.put(key, client_2.get(key))

        elif a1_action == StateAction.UPDATE and a2_action is None:
            print('Updating', client_2, 'for', key)
            client_2.put(key, client_1.get(key))

        elif a1_action is None and a2_action == StateAction.DELETE:
            print('Deleting', key, 'in', client_1)
            client_1.delete(key)

        elif a1_action == StateAction.DELETE and a2_action is None:
            print('Deleting', key, 'in', client_2)
            client_2.delete(key)

        else:
            print('There is a conflict:', key, a1, a2)

    print('Updating Indexes')
    client_2.update_index()
    client_1.update_index()
