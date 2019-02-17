FROM ubuntu:16.04

ENV ROOTDIR /usr/local/
ENV APPDIR /usr/src/app

WORKDIR $ROOTDIR/

RUN apt-get update && apt-get install -y build-essential \
    libssl-dev \
    libffi-dev \
    python-dev \
    python-psycopg2 \
    python-mysqldb \
    python-setuptools \
    libgnutls-dev \
    libcurl4-gnutls-dev

RUN apt install -y libcurl4-openssl-dev libssl-dev
RUN apt install -y python-pip

RUN pip install --upgrade pip
RUN pip install --upgrade virtualenv
RUN pip install --upgrade setuptools
RUN pip install virtualenv

RUN apt install -y chromium-chromedriver

WORKDIR $APPDIR