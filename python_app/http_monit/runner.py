#!/bin/env python3
import csv
import datetime
import sys
import typing

import click

REMOTE = 0
EPOCH = 3
REQUEST = 4
STATUS = 5
BYTES = 6

global_time = 0


class AlertManager:
    def __init__(self, load_threshold: int = 10, alert_window: int = 120) -> None:
        self._load_threshold = load_threshold
        self._alert_window = alert_window
        self._alert_triggered = False


class MetricManager:
    def __init__(self) -> None:
        self._tsdb = dict()
        self._time = 0
        self._last_logging_milestone = 0

        self._subscribed_alert_managers = []

    def attach_alert_manager(self, alert_manager: AlertManager) -> None:
        self._subscribed_alert_managers.append(alert_manager)

    def _print_metrics(self, until_time: int) -> None:
        """
        Prints the metrics from the internal time series database between the two times.
        :param until_time: time until where it should be collecting metrics.
        """
        total_hits = 0
        total_traffic = 0
        inbound_traffic = 0
        outbound_traffic = 0
        requests_dictionaries = {"method": {}, "section": {}, "remote": {}, "status": {}}

        times = sorted(self._tsdb.keys(), reverse=True)
        for t in times:
            if t > until_time:
                continue

            hits = self._tsdb[t]
            total_hits += len(hits)
            for hit in hits:
                total_traffic += hit["bytes"]
                if hit["method"] == "GET":
                    outbound_traffic += hit["bytes"]
                else:
                    inbound_traffic += hit["bytes"]

                for name, requests_dictionary in requests_dictionaries.items():
                    if hit[name] in requests_dictionary:
                        requests_dictionary[hit[name]] += 1
                    else:
                        requests_dictionary[hit[name]] = 0

            if t == self._last_logging_milestone:
                break

        from_time_str = datetime.datetime.fromtimestamp(self._last_logging_milestone)
        print(f"Statistics for the interval {from_time_str} - {datetime.datetime.fromtimestamp(until_time)}")
        print("=====================================================================")
        print(f"total requests: {total_hits}")
        print(f"total bytes transferred: {total_traffic}")
        print(f"inbound bytes transferred: {inbound_traffic}")
        print(f"outbound bytes transferred: {outbound_traffic}")
        self._print_request_dictionaries(requests_dictionaries)
        print("")

    @staticmethod
    def _print_request_dictionaries(request_dictionaries: dict[str, dict[str, int]]):
        """
        Prints the requests per type and subtype.
        :param request_dictionaries: type and subtype of the requests.
        """
        for name, request_dictionary in request_dictionaries.items():
            if request_dictionary:
                print(f"requests per {name}:")
                for k, v in request_dictionary.items():
                    print(f"\t{name}: {k}; requests: {v}")

    def process_log_line(self, line: list[str]) -> None:
        """
        Parses the log line and stores it in its internal time series database.
        It also updates the internal system time.
        :param line: Log line to process.
        """
        int_time = int(line[EPOCH])
        if int_time not in self._tsdb:

            # Time only goes forward, so we will only update the clock when we find a new higher value
            if int_time > self._time:
                self._time = int_time

            if len(self._tsdb) > 1:
                times = sorted(self._tsdb.keys(), reverse=True)
                if self._last_logging_milestone == 0:
                    self._last_logging_milestone = times[-1]
                delta = self._time - self._last_logging_milestone
                while delta > 9:
                    self._print_metrics(self._last_logging_milestone + 9)
                    self._last_logging_milestone += 9
                    delta = delta - self._last_logging_milestone

            self._tsdb[int_time] = []

        method = line[REQUEST].split()[0]
        section = '/' + line[REQUEST].split()[1].split('/')[1]
        remote = line[REMOTE]
        status = line[STATUS]
        bytes_transferred = int(line[BYTES])
        self._tsdb[int_time].append(
            {"method": method, "section": section, "remote": remote, "status": status, "bytes": bytes_transferred}
        )


def _process_log_file(csvfile: typing.Any,  mm: MetricManager) -> None:
    """
    Processes the log file line by line.
    :param csvfile: Iterable object that contains the log data.
    :param mm: Object in charge of managing the metric database.
    """
    logreader = csv.reader(csvfile)
    next(logreader)
    for row in logreader:
        mm.process_log_line(row)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--log_file_path', '-f', help='Path of the file that contains the log data.', type=click.File('r'),
              default=sys.stdin)
@click.option('--request_threshold', '-t', help='Request threshold for traffic alerting.', default=10, type=int)
def main(log_file_path: click.File, request_threshold: int):
    """
    Monitors an http log file and shows statistics and alerts on high load conditions.
    """
    mm = MetricManager()
    am = AlertManager(load_threshold=request_threshold)
    mm.attach_alert_manager(am)
    if isinstance(log_file_path, click.File):
        with open(log_file_path.name, 'r') as csvfile:
            _process_log_file(csvfile, mm)
    else:
        _process_log_file(log_file_path, mm)


if __name__ == '__main__':
    main()
