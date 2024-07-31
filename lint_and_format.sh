#!/bin/bash

# Stop script if any command fails
set -e

# Run black
black .

# Run isort
isort .

# Run flake8
flake8 .

# Run pylint
pylint app
