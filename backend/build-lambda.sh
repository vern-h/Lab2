#!/bin/bash
# Build Lambda zip on Linux (Docker) so pydantic_core works on Lambda.
set -e
cd "$(dirname "$0")"
rm -rf package lambda-deploy.zip
docker run --rm -v "$(pwd)":/var/task public.ecr.aws/lambda/python:3.12 \
  bash -c "pip install -r requirements.txt -t package/ && cp main.py package/ && cd package && zip -r ../lambda-deploy.zip ."
echo "Done: lambda-deploy.zip (upload this to Lambda)"
