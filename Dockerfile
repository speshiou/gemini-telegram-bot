FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update

COPY . /src
WORKDIR /src

# a temporary directory for processing images
RUN mkdir -p /tmp/images
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]