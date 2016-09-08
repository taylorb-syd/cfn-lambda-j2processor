#!/bin/bash -xe
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ZIPNAME=cfn-lambda-j2processor.zip
cd $DIR
git submodule init
git submodule update
mkdir -p compile
rm -fdr compile/*
cp -r lambda_function.py compile/
cp -r modules/boto3/boto3 compile/
cp -r modules/botocore/botocore compile/
cp -r modules/cfnlambda/cfnlambda.py compile/
cp -r modules/dateutil/dateutil compile/
cp -r modules/jinja/jinja2 compile/
cp -r modules/jmespath.py/jmespath compile/
cp -r modules/markupsafe/markupsafe compile/
cp -r modules/s3transfer/s3transfer compile/
cd compile
zip -9r $ZIPNAME *
mv $ZIPNAME $DIR/
cd $DIR
rm -fdr compile/*
