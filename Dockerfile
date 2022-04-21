FROM python:3

WORKDIR /app
COPY python_app /app

#RUN python3 -m venv my_virtualenv && . my_virtualenv/bin/activate && pip3 install -e .
RUN pip3 install -e .
