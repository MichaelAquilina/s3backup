# -*- coding: utf-8 -*-

import logging
import traceback

from s4.clients import SyncState
from s4.resolution import Resolution


class SyncWorker(object):
    def __init__(
        self,
        client_1,
        client_2,
        start_callback=None,
        update_callback=None,
        complete_callback=None,
        action_callback=None,
        conflict_handler=None,
    ):
        self.client_1 = client_1
        self.client_2 = client_2
        self.logger = logging.getLogger(str(self))
        self.start_callback = start_callback
        self.update_callback = update_callback
        self.complete_callback = complete_callback
        self.action_callback = action_callback
        self.conflict_handler = conflict_handler

    def __repr__(self):
        return "SyncWorker<{}, {}>".format(
            self.client_1.get_uri(), self.client_2.get_uri()
        )

    def sync(self, conflict_choice=None, keys=None, dry_run=False):
        self.client_1.lock()
        self.client_2.lock()
        try:
            resolutions, unhandled_events = self.get_sync_states(keys)

            self.logger.debug(
                "There are %s unhandled events for the user to solve",
                len(unhandled_events),
            )
            self.logger.debug(
                "There are %s automatically resolved calls", len(resolutions)
            )
            for key in sorted(unhandled_events.keys()):
                action_1, action_2 = unhandled_events[key]
                if conflict_choice == "1":
                    resolutions[key] = Resolution.get_resolution(
                        key, action_1, self.client_2, self.client_1
                    )
                elif conflict_choice == "2":
                    resolutions[key] = Resolution.get_resolution(
                        key, action_2, self.client_1, self.client_2
                    )
                if self.conflict_handler is not None:
                    resolution = self.conflict_handler(
                        key, action_1, self.client_1, action_2, self.client_2
                    )
                    if resolution is not None:
                        resolutions[key] = resolution
                    else:
                        self.logger.info("Ignoring sync conflict for %s", key)
                else:
                    self.logger.info("Unable to resolve conflict for %s", key)

            self.run_resolutions(resolutions, dry_run)

        finally:
            self.client_1.unlock()
            self.client_2.unlock()

    def get_sync_states(self, keys=None):
        # we store a list of resolutions to make sure we can handle everything before
        # running any updates on the file system and indexes
        resolutions = {}

        # list of unhandled events which cannot be solved automatically (or alternatively the
        # the automated solution has not yet been implemented)
        unhandled_events = {}

        self.logger.debug("Generating deferred calls based on client states")
        for key, state_1, state_2 in self.get_states(keys):
            self.logger.debug("%s: %s %s", key, state_1, state_2)
            if (
                state_1.state == SyncState.NOCHANGES
                and state_2.state == SyncState.NOCHANGES
            ):
                if state_1.remote_timestamp == state_2.remote_timestamp:
                    continue
                elif state_1.remote_timestamp > state_2.remote_timestamp:
                    resolutions[key] = Resolution(
                        Resolution.UPDATE,
                        self.client_2,
                        self.client_1,
                        key,
                        state_1.remote_timestamp,
                    )
                elif state_2.remote_timestamp > state_1.remote_timestamp:
                    resolutions[key] = Resolution(
                        Resolution.UPDATE,
                        self.client_1,
                        self.client_2,
                        key,
                        state_2.remote_timestamp,
                    )

            elif (
                state_1.state == SyncState.CREATED
                and state_2.state == SyncState.DOESNOTEXIST
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_2,
                    self.client_1,
                    key,
                    state_1.local_timestamp,
                )

            elif (
                state_2.state == SyncState.CREATED
                and state_1.state == SyncState.DOESNOTEXIST
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_1,
                    self.client_2,
                    key,
                    state_2.local_timestamp,
                )

            elif (
                state_1.state == SyncState.NOCHANGES
                and state_2.state == SyncState.DOESNOTEXIST
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_2,
                    self.client_1,
                    key,
                    state_1.remote_timestamp,
                )

            elif (
                state_2.state == SyncState.NOCHANGES
                and state_1.state == SyncState.DOESNOTEXIST
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_1,
                    self.client_2,
                    key,
                    state_2.remote_timestamp,
                )
            elif (
                state_1.state == SyncState.UPDATED
                and state_2.state == SyncState.DOESNOTEXIST
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_2,
                    self.client_1,
                    key,
                    state_1.local_timestamp,
                )

            elif (
                state_2.state == SyncState.UPDATED
                and state_1.state == SyncState.DOESNOTEXIST
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_2,
                    self.client_1,
                    key,
                    state_1.local_timestamp,
                )

            elif state_1.state in (
                SyncState.DELETED,
                SyncState.DOESNOTEXIST,
            ) and state_2.state in (SyncState.DELETED, SyncState.DOESNOTEXIST):
                # nothing to do, they have already both been deleted/do not exist
                continue

            elif (
                state_1.state == SyncState.UPDATED
                and state_2.state == SyncState.NOCHANGES
                and state_1.remote_timestamp == state_2.remote_timestamp
            ):
                resolutions[key] = Resolution(
                    Resolution.UPDATE,
                    self.client_2,
                    self.client_1,
                    key,
                    state_1.local_timestamp,
                )

            elif (
                state_2.state == SyncState.UPDATED
                and state_1.state == SyncState.NOCHANGES
                and state_1.remote_timestamp == state_2.remote_timestamp
            ):
                resolutions[key] = Resolution(
                    Resolution.UPDATE,
                    self.client_1,
                    self.client_2,
                    key,
                    state_2.local_timestamp,
                )

            elif (
                state_1.state == SyncState.DELETED
                and state_2.state == SyncState.NOCHANGES
                and state_1.remote_timestamp == state_2.remote_timestamp
            ):
                resolutions[key] = Resolution(
                    Resolution.DELETE,
                    self.client_2,
                    None,
                    key,
                    state_1.remote_timestamp,
                )

            elif (
                state_2.state == SyncState.DELETED
                and state_1.state == SyncState.NOCHANGES
                and state_1.remote_timestamp == state_2.remote_timestamp
            ):
                resolutions[key] = Resolution(
                    Resolution.DELETE,
                    self.client_1,
                    None,
                    key,
                    state_2.remote_timestamp,
                )

            elif (
                state_1.state == SyncState.DELETED
                and state_2.state == SyncState.CREATED
                and state_1.remote_timestamp == state_2.remote_timestamp
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_1,
                    self.client_2,
                    key,
                    state_2.local_timestamp,
                )

            elif (
                state_2.state == SyncState.DELETED
                and state_1.state == SyncState.CREATED
                and state_1.remote_timestamp == state_2.remote_timestamp
            ):
                resolutions[key] = Resolution(
                    Resolution.CREATE,
                    self.client_2,
                    self.client_1,
                    key,
                    state_1.local_timestamp,
                )

            else:
                unhandled_events[key] = (state_1, state_2)

            self.logger.debug("Action=%s", resolutions.get(key))

        return resolutions, unhandled_events

    def run_resolutions(self, resolutions, dry_run=False):
        # call everything once we know we can handle all of it
        self.logger.debug("There are %s total deferred calls", len(resolutions))
        success = []
        try:
            for key in sorted(resolutions.keys()):
                resolution = resolutions[key]
                if self.action_callback is not None:
                    self.action_callback(resolution)

                if resolution.action == Resolution.UPDATE:
                    deferred_function = self.move_client
                elif resolution.action == Resolution.CREATE:
                    deferred_function = self.move_client
                elif resolution.action == Resolution.DELETE:
                    deferred_function = self.delete_client
                else:
                    raise ValueError("Unknown resolution", resolution)

                if dry_run:
                    continue

                try:
                    deferred_function(resolution)
                    self.client_1.update_index_entry(key)
                    self.client_2.update_index_entry(key)
                    success.append(key)
                except Exception as e:
                    self.logger.error(
                        "An error occurred while trying to update %s:\n%s", key, e
                    )
                    self.logger.debug(traceback.format_exc())
        except KeyboardInterrupt:
            self.logger.warning(
                "Session interrupted by Keyboard Interrupt. Cleaning up...."
            )

        if len(success) > 0:
            self.logger.info("Flushing Index to Storage")
            self.client_1.flush_index()
            self.client_2.flush_index()
        else:
            self.logger.info("Nothing to update")

        return success

    def get_states(self, keys=None):
        client_1_actions = self.client_1.get_all_actions()
        client_2_actions = self.client_2.get_all_actions()

        all_keys = set(client_1_actions) | set(client_2_actions)
        self.logger.debug(
            "%s keys in total (%s for %s and %s for %s)",
            len(all_keys),
            len(client_1_actions),
            self.client_1.get_uri_local(),
            len(client_2_actions),
            self.client_2.get_uri_local(),
        )
        if keys is None:
            target_keys = sorted(all_keys)
        else:
            target_keys = keys

        DOES_NOT_EXIST = SyncState(SyncState.DOESNOTEXIST, None, None)
        for key in target_keys:
            action_1 = client_1_actions.get(key, DOES_NOT_EXIST)
            action_2 = client_2_actions.get(key, DOES_NOT_EXIST)
            yield key, action_1, action_2

    def move_client(self, resolution):
        sync_object = resolution.from_client.get(resolution.key)
        if self.start_callback is not None:
            self.start_callback(sync_object)

        resolution.to_client.put(
            resolution.key, sync_object, callback=self.update_callback
        )

        if self.complete_callback is not None:
            self.complete_callback(sync_object)

        resolution.to_client.set_remote_timestamp(resolution.key, resolution.timestamp)
        resolution.from_client.set_remote_timestamp(
            resolution.key, resolution.timestamp
        )

    def delete_client(self, resolution):
        resolution.to_client.delete(resolution.key)
        resolution.to_client.set_remote_timestamp(resolution.key, resolution.timestamp)
