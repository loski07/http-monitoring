FROM python:3

WORKDIR /app
COPY python_app /app

RUN pip3 install -e .
