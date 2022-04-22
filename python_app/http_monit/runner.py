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

GREEN = '\033[92m'  # GREEN
RED = '\033[91m'  # RED
RESET = '\033[0m'  # RESET COLOR


class AlertManager:
    def alert(self, value: int, time: int) -> None:
        pass

    def end_alert(self, time: int) -> None:
        pass

    def info(self, data: dict) -> None:
        pass


class ConsoleAlertManager(AlertManager):
    def __init__(self):
        self._alert_triggered = False

    def alert(self, value: int, time: int) -> None:
        if self._alert_triggered:
            return
        str_time = datetime.datetime.fromtimestamp(time)
        print(f"\n{RED}High traffic generated an alert - hits = {value}, triggered at {str_time}{RESET}\n")
        self._alert_triggered = True

    def end_alert(self, time: int) -> None:
        if not self._alert_triggered:
            return
        print(f"\n{GREEN}Traffic restored. Alert terminated at {datetime.datetime.fromtimestamp(time)}{RESET}\n")
        self._alert_triggered = False

    def info(self, data: dict) -> None:
        for k, v in data.items():
            print(k)
            print("=======================================================================")
            if isinstance(v, dict):
                for k1, v1 in v.items():
                    if isinstance(v1, dict):
                        for k2, v2 in v1.items():
                            print(f"{k1} {k2}:")
                            for k3, v3 in v2.items():
                                print(f"\t{k2}: {k3}; requests: {v3}")
                    else:
                        print(f"{k1}: {v1}")
        print("")


class Subscriber:
    def tick(self, producer: typing.Any) -> None:
        """
        Informs the subscriber of a new clock cycle.
        :param producer: object it is subscribed to.
        """
        pass


class EventManager(Subscriber):
    def __init__(self, seconds_between_metrics_printouts: int = 10, load_alert_window: int = 120,
                 load_alert_threshold: int = 10, alert_manager: AlertManager = ConsoleAlertManager()):
        """
        Constructor of the object that initializes its internal attributes with the parameters.
        :param seconds_between_metrics_printouts: Time window between showing information.
        :param load_alert_window: Time window for alert computing.
        :param load_alert_threshold: Maximum load value tolerated.
        :param alert_manager: Object that takes care of alerting and printing information.
        """
        self._seconds_between_metrics_printouts = seconds_between_metrics_printouts
        self._pending_ticks_for_next_stats = seconds_between_metrics_printouts
        self._load_alert_threshold = load_alert_threshold
        self._load_alert_window = load_alert_window
        self._alert_manager = alert_manager

    def tick(self, mm: typing.Any) -> None:
        """
        Informs the event manager of a new clock cycle so it can check the load and the statistics and ask to show them
        if the conditions require it.
        :param mm: Metrics manager from where to collect data.
        """
        load = mm.get_load(self._load_alert_window)
        if load > self._load_alert_threshold:
            self._alert_manager.alert(load, mm.time)
        else:
            self._alert_manager.end_alert(mm.time)

        self._pending_ticks_for_next_stats -= 1
        if self._pending_ticks_for_next_stats == 0:
            self._pending_ticks_for_next_stats = self._seconds_between_metrics_printouts
            metrics = mm.get_metrics(self._seconds_between_metrics_printouts)
            self._alert_manager.info(metrics)


class MetricManager:
    def __init__(self, event_manager: EventManager) -> None:
        """
        Constructor of the object that initializes its internal attributes with the parameters.
        :param event_manager: Object that will take care of the events produced.
        """
        self._tsdb = dict()
        self.time = 0
        self._subscribed_managers = []
        self._event_manager = event_manager

    def get_load(self, time_window: int) -> int:
        """
        Computes the amount of traffic for the last interval.
        :param time_window: Number of seconds that define the interval.
        :return: Total traffic during the interval
        """
        total_hits = 0
        times = sorted(self._tsdb.keys(), reverse=True)
        for t in times:
            if t > self.time:
                continue
            hits = self._tsdb[t]
            total_hits += len(hits)
            if t <= self.time - time_window:
                break
        return total_hits

    def get_metrics(self, time_window: int) -> dict:
        """
        Collects the metrics from the internal time series database for the last interval.
        :param time_window: Number of seconds that define the interval.
        """
        total_hits = 0
        total_traffic = 0
        inbound_traffic = 0
        outbound_traffic = 0
        requests_dictionaries = {"method": {}, "section": {}, "remote": {}, "status": {}}

        times = sorted(self._tsdb.keys(), reverse=True)
        for t in times:
            if t > self.time:
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

            if t <= self.time - time_window:
                break

        from_time_str = datetime.datetime.fromtimestamp(self.time - time_window)
        title = f"Statistics for the interval [{from_time_str} - {datetime.datetime.fromtimestamp(self.time)})"
        metrics = {title: {
                        "total requests": total_hits,
                        "total bytes transferred": total_traffic,
                        "inbound bytes transferred": inbound_traffic,
                        "outbound bytes transferred": outbound_traffic,
                        "requests per": requests_dictionaries}
                   }
        return metrics

    def _tick(self, time_in_file: int) -> bool:
        """
        Evaluates if the time passed as parameter means a new second in the internal clock. If the time is higher than
        the internal clock, it will advance it a second and notify that a clock tick has been consumed.
        :param time_in_file: Epoch from the log line currently parsed
        :return: True if the parameter the epoch is bigger than the internal clock.
        """
        if self.time == 0:
            self.time = time_in_file
            return False

        if self.time < time_in_file:
            self.time += 1
            self._event_manager.tick(self)
            return True
        else:
            return False

    def process_log_line(self, line: list[str]) -> None:
        """
        Parses the log line and stores it in its internal time series database.
        It also updates the internal system time.
        :param line: Log line to process.
        """
        int_time = int(line[EPOCH])
        new_tick = self._tick(int_time)
        while new_tick:
            new_tick = self._tick(int_time)

        if int_time not in self._tsdb:
            self._tsdb[int_time] = []
        method = line[REQUEST].split()[0]
        section = '/' + line[REQUEST].split()[1].split('/')[1]
        remote = line[REMOTE]
        status = line[STATUS]
        bytes_transferred = int(line[BYTES])
        self._tsdb[int_time].append(
            {"method": method, "section": section, "remote": remote, "status": status, "bytes": bytes_transferred}
        )


def _process_log_file(csvfile: typing.Any, mm: MetricManager) -> None:
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
    mm = MetricManager(EventManager(load_alert_threshold=request_threshold))

    if isinstance(log_file_path, click.File):
        with open(log_file_path.name, 'r') as csvfile:
            _process_log_file(csvfile, mm)
    else:
        _process_log_file(log_file_path, mm)


if __name__ == '__main__':
    main()
