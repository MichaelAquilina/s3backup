#! -*- encoding: utf-8 -*-
from collections import defaultdict

from s4.commands import Command

from watchdir import WatchDir
import os

class DaemonCommand(Command):
    def run(self, terminator=lambda x: False):
        all_targets = list(self.config["targets"].keys())
        if not self.args.targets:
            targets = all_targets
        else:
            targets = self.args.targets

        if not targets:
            self.logger.info("No targets available")
            self.logger.info('Use "add" command first')
            return

        for target in targets:
            if target not in self.config["targets"]:
                self.logger.info("Unknown target: %s", target)
                return

        notifier = WatchDir()

        watch_map = {}

        for target in targets:
            entry = self.config["targets"][target]
            path = entry["local_folder"]
            self.logger.info("Watching %s", path)
            notifier.add_watch(path, True, target)

            # Check for any pending changes
            worker = self.get_sync_worker(target)
            worker.sync(conflict_choice=self.args.conflicts)

        index = 0
        while not terminator(index):
            index += 1

            to_run = set()
            
            event = notifier.read(read_delay=self.args.read_delay)
            while event is not None:
                # Dont bother running for .index
                if os.path.basename(event.fullname) not in (".index", ".s4lock"):
                    to_run.add(target)

                event = notifier.readAll(read_delay=self.args.read_delay)

            for target in to_run:
                worker = self.get_sync_worker(target)

                # Should ideally be setting keys to sync
                self.logger.info("Syncing {}".format(worker))
                worker.sync(conflict_choice=self.args.conflicts)
