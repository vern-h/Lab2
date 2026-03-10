#!/bin/bash
# Build zip for Lambda from Mac by asking pip for Linux wheels.
# If you still get pydantic_core error, use build-lambda.sh (Docker) instead.
set -e
cd "$(dirname "$0")"
rm -rf package lambda-deploy.zip
pip install --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all: -r requirements.txt -t package/
cp main.py package/
cd package && zip -r ../lambda-deploy.zip . && cd ..
echo "Done: lambda-deploy.zip"
