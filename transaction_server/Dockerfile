# syntax=docker/dockerfile:1
FROM python:3.9-alpine
WORKDIR /app
ENV FLASK_APP=transaction_server
ENV FLASK_RUN_HOST=0.0.0.0
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . transaction_server/