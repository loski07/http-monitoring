
# HTTP log monitoring console program
## Task description
- Read a CSV-encoded HTTP access log. It should either take the file as a
parameter or read from standard input. All time-based calculations should be
relative to the timestamps in the log-file. Avoid using system time in your
program.
Example log file (first line is the header):
```text
"remotehost","rfc931","authuser","date","request","status","bytes"
"10.0.0.1","-","apache",1549574332,"GET /api/user HTTP/1.0",200,1234
"10.0.0.4","-","apache",1549574333,"GET /report HTTP/1.0",200,1136
"10.0.0.1","-","apache",1549574334,"GET /api/user HTTP/1.0",200,1194
"10.0.0.4","-","apache",1549574334,"POST /report HTTP/1.0",404,1307

```
- For every 10 seconds of log lines, display stats about the traffic during those 10s:
the sections of the web site with the most hits, as well as statistics that might be
useful for debugging. A section is defined as being what's before the second '/' in
the resource section of the log line. For example, the section for "/api/user" is
"/api" and the section for "/report" is "/report"
- Whenever total traffic for the past 2 minutes exceeds a certain number on
average, print a message to the console saying that “High traffic generated an
alert - hits = {value}, triggered at {time}”. The default threshold should be 10
requests per second but should be configurable
- Whenever the total traffic drops again below that value on average for the past 2
minutes, print another message detailing when the alert recovered, +/- a second
- Consider the efficiency of your solution and how it would scale to process high
volumes of log lines - don't assume you can read the entire file into memory
- Write your solution as you would any piece of code that others might need to
modify and maintain, both in terms of structure and style
- Write a test for the alerting logic
- Explain how you’d improve on this application design

You can find the log file [here](./http-access-log.csv)

## Guidelines and clarifications
- The time in the alert message can be formatted however you like (using a
timestamp or something more readable are both fine), but the time cited must be
in terms of when the alert or recovery was triggered in the log file, not the current
time
- Make a reasonable assumption about how to handle the 10-second intervals,
there are a couple of valid options here. Make a similar assumption about how
frequently stats should be displayed as you process (but don't just print them at
the end!)
- Try to make only one pass over the file overall, for both the statistics and the
alerting, as if you were reading it in real time
- The date is in [Unix time](https://en.wikipedia.org/wiki/Unix_time)
- You are free to use standard and open
source libraries, but the core of the alerting logic must be your own

- Duplicate alerts should not be triggered - a second alert should not be triggered
before a recovery of the first
- The alerting state does not need to persist across program runs
- Package your source code along with instructions on how to run it into a zip/tar
file of some sort

## Run instructions
### Prerequisites
- Python 3
- Docker desktop (optional)
- Zip file with the application
- cd-ing to the working directory
```shell
unzip http-monitoring.unzip
cd http-monitoring
```
### Using Docker
- Building the image:
```shell
docker build . -t http_monit:v1.0
```
- Running the container
```shell
docker run --name http_monit -v $(pwd):/data http_monit:v1.0 http_monit -f /data/http-access-log.csv
```
### Installing the wheel into a virtual environment
```shell
python3 -m venv my_virtualenv
source my_virtualenv/bin/activate
pip3 install -e python_app
http_monit -f ./http-access-log.csv
```

### Executing the python program
```shell
python3 -m venv my_virtualenv
source my_virtualenv/bin/activate
pip install -r python_app/requirements.txt
python ./python_app/http_monit/runner.py -f ./http-access-log.csv
```
## Implementation details
### Assumptions
- The first row of the file or stdin input is considered the header and will be ignored.
- The system will keep an internal clock based on the timestamp of the lines of the file. It will be initialized to the
first timestamp and updated every time a timestamp of a line is bigger than the clock. If the first lines of the file
are similar to the following snippet, the clock will be initialized to `1549573860` and the metrics prior to that
(`1549573859`) will be stored but not taken in consideration as they were produced before the beginning of times.
```text
"remotehost","rfc931","authuser","date","request","status","bytes"
"10.0.0.2","-","apache",1549573860,"GET /api/user HTTP/1.0",200,1234
"10.0.0.4","-","apache",1549573860,"GET /api/user HTTP/1.0",200,1234
"10.0.0.5","-","apache",1549573860,"GET /api/help HTTP/1.0",200,1234
"10.0.0.4","-","apache",1549573859,"GET /api/help HTTP/1.0",200,1234
```
- Every time the internal clock is updated, all the subscribed manager will be notified of the tick. The event manager
subscribed to the metrics manager will ask the metric manager for the load of the last 120 seconds and trigger an alert
if that load is higher than the threshold. In addition to that, will keep track of when was the last time it asked the
metrics manager to print statistics and if it was 10 seconds ago, it will ask the metrics manager to do it.
(see method [process_log_line](./python_app/http_monit/runner.py))

- We will show the following statistics per interval (closed interval on the left, open on the right)
```text
Statistics for the interval [2019-02-07 22:11:00 - 2019-02-07 22:11:10)
=======================================================================
total requests: 80
total bytes transferred: 98518
inbound bytes transferred: 26368
outbound bytes transferred: 72150
requests per method:
	method: GET; requests: 58
	method: POST; requests: 20
requests per section:
	section: /api; requests: 52
	section: /report; requests: 26
requests per remote:
	remote: 10.0.0.2; requests: 18
	remote: 10.0.0.4; requests: 10
	remote: 10.0.0.1; requests: 19
	remote: 10.0.0.3; requests: 10
	remote: 10.0.0.5; requests: 18
requests per status:
	status: 200; requests: 65
	status: 404; requests: 9
	status: 500; requests: 3
```

### How to test the alarm logic
In order to test the alarm logic, I created a pyunit test. I created a test `AlertManager` that will trigger custom
exceptions when the alarm is triggered and when it is cancelled, so they can easily be caught and analyzed. 
I also created a test file with the following request per second pattern.
```text
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
```
The system is configured to alert if the load during the last 2 seconds is higher than 5, so, when we get the
6th tick comes we will have the load of the second 4 (1 request) and the second 5 (8 requests), so 9 in total.
That means that the system must raise an alarm.

The load stabilizes in 8 hits per second until second 10. That condition is an alert condition but no alert
should be triggered as the alert has been triggered before.

When tick 12 comes, the load for the last 2 seconds was 1 request (second 10) and 1 request (second 11) so the 
alarm should be cancelled informing that in second 11 the condition was resolved.

#### How to run the alarm test
Once you have coverer the [prerequisites](#Prerequisites) you can simply run:
```shell
PYTHONPATH=PYTHONPATH:./python_app python python_app/http_monit_tests/test_alert.py
```

## How to improve the application
- Use a real time series database for storing the metrics.
- Use have a distributed ingestion of the metrics for horizontal scale (given that the database was already extracted from the
implementation)
