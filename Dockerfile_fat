FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.4

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive TZ=Europe/Berlin apt-get install -y libspatialindex-dev unar bc python3-pip wget

ADD ./requirements.txt .
RUN pip install -r requirements.txt
RUN pip install GDAL --global-option=build_ext --global-option="-I/usr/include/gdal"

RUN mkdir /code
COPY ./gdal_interfaces.py /code/
COPY ./server.py /code/
COPY ./config.ini /code/

WORKDIR /code
CMD python3 server.py

EXPOSE 8080

EXPOSE 8443
