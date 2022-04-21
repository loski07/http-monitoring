
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
first timestamp and updated every time a timestamp of a line is bigger than the clock.
- Every time the internal clock is updated, the system will check if we have spent 10 seconds from the beginning of the
execution. If that is the case we will print the statistics for those 10 seconds.
(see method [process_log_line](./python_app/http_monit/runner.py))

- We will show the following statistics per interval
```text
Statistics for the interval 2019-02-07 22:18:38 - 2019-02-07 22:18:47
=====================================================================
total requests: 20
total bytes transferred: 24551
inbound bytes transferred: 6218
outbound bytes transferred: 18333
requests per method:
	method: GET; requests: 14
	method: POST; requests: 4
requests per section:
	section: /api; requests: 9
	section: /report; requests: 9
requests per remote:
	remote: 10.0.0.1; requests: 8
	remote: 10.0.0.3; requests: 0
	remote: 10.0.0.5; requests: 6
	remote: 10.0.0.2; requests: 2
requests per status:
	status: 500; requests: 3
	status: 200; requests: 14
	status: 404; requests: 0
```
