FROM python:3.11-alpine as build

RUN apk update
RUN apk add libspatialindex-dev --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing/
RUN apk add gdal-dev build-base

ADD ./requirements.txt .
RUN mkdir /wheels
RUN pip wheel -r requirements.txt -w /wheels
RUN pip wheel GDAL -w /wheels --global-option=build_ext --global-option="-I/usr/include/gdal"

FROM python:3.11-alpine
RUN mkdir /wheels
COPY --from=build /wheels /wheels
RUN apk add gdal-dev
RUN pip install /wheels/*.whl
RUN pip install gunicorn gevent eventlet
RUN rm -rf /wheels
RUN mkdir /code
COPY ./gdal_interfaces.py /code/
COPY ./server.py /code/
WORKDIR /code
EXPOSE 8080
CMD python3 -m gunicorn -b 0.0.0.0:8080 --worker-class gevent -w 12 server:app