#!/usr/bin/env bash

OUTDIR="./data"
if [ ! -e $OUTDIR ] ; then
    echo $OUTDIR does not exist!
fi

CUR_DIR=$(pwd)

set -eu

cd $OUTDIR
../open-elevation/download-srtm-data.sh
../open-elevation/create-tiles.sh SRTM_NE_250m.tif 10 10
../open-elevation/create-tiles.sh SRTM_SE_250m.tif 10 10
../open-elevation/create-tiles.sh SRTM_W_250m.tif 10 20
rm -rf SRTM_NE_250m.tif SRTM_SE_250m.tif SRTM_W_250m.tif *.rar

cd $CUR_DIR
