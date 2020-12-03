FROM python:3.8

RUN pip install \
    autopep8 \
    black \
    codecov \
    flake8 \
    mutmut \
    numpy \
    pandas \
    pylint \
    pylint-fail-under \
    pytest-cov \
    pytest==5.0.1

WORKDIR /workdir
