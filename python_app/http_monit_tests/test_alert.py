import unittest
from http_monit import runner
import os
import csv
import io
import sys


def foo(in_str):
    print("hi " + in_str)


class AlertRaised(Exception):
    pass


class AlertFixed(Exception):
    pass


class TestAlertManager(runner.AlertManager):
    def __init__(self):
        self._alert_triggered = False

    def alert(self, value: int, time: int) -> None:
        if self._alert_triggered:
            return
        self._alert_triggered = True
        raise AlertRaised(value, time)

    def end_alert(self, time: int) -> None:
        if not self._alert_triggered:
            return
        self._alert_triggered = False
        raise AlertFixed(time)


class LoadAlertTestCase(unittest.TestCase):

    def setUp(self) -> None:
        """
        Sets up the environment for the test.
        It creates an EventManager configured, so it will alert if the load on the last 2 seconds is higher than 5
        requests. If it is lower than 5 for the last 2 seconds he will resolve the alert.
        """
        self.mm = runner.MetricManager(
            runner.EventManager(
                load_alert_threshold=5, load_alert_window=2, alert_manager=TestAlertManager()))

    def test_alert(self):
        """
        Test for the alerting mechanism. It reads a test access log file whose requests per second follow the graph
        below

        r |
        e |
        q |                     *   *   *   *   *
          |                     *   *   *   *   *
          |                     *   *   *   *   *
          |                     *   *   *   *   *
          |                     *   *   *   *   *
          |                     *   *   *   *   *
          |                     *   *   *   *   *
          | *   *   *   *   *   *   *   *   *   *   *   *   *
          |___ ___ ___ ___ ___ ___ ___ ___ ___ ___ ___ ___ ___ ___ ___ ___ ___   time
            0   1   2   3   4   5   6   7   8   9   10  11  12  13  14  15  16

        The system is configured to alert if the load during the last 2 seconds is higher than 5, so, when we get the
        6th tick comes we will have the load of the second 4 (1 request) and the second 5 (8 requests), so 9 in total.
        That means that the system must raise an alarm.

        The load stabilizes in 8 hits per second until second 10. That condition is an alert condition but no alert
        should be triggered as the alert has been triggered before.

        When tick 12 comes, the load for the last 2 seconds was 1 request (second 10) and 1 request (second 11) so the
        alarm should be cancelled informing that in second 11 the condition was resolved.

        """
        with open(os.path.join(os.path.dirname(__file__), 'test-access-log.csv'), 'r') as csvfile:
            logreader = csv.reader(csvfile)
            next(logreader)
            alert_raised = False
            alert_fixed = False
            for line in logreader:
                try:
                    self.mm.process_log_line(line)
                except AlertRaised as ar:
                    self.assertEqual((9, 1000000006), ar.args)
                    alert_raised = True
                except AlertFixed as af:
                    self.assertEqual((1000000011,), af.args)
                    alert_fixed = True
            self.assertTrue(alert_raised == alert_fixed == True)


if __name__ == '__main__':
    unittest.main()
