FROM python:3.5-alpine
COPY . /code
WORKDIR /code
ENV QREMIS_API_CONFIG /code/config.py
RUN python setup.py install
RUN pip install gunicorn
ARG PORT="8911"
ARG WORKERS="4"
ARG TIMEOUT="30"
ENV PORT=$PORT WORKERS=$WORKERS TIMEOUT=$TIMEOUT
CMD gunicorn qremis_api:app -w ${WORKERS} -t ${TIMEOUT} -b 0.0.0.0:${PORT}
