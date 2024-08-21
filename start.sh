#!/bin/bash

# Install any dependencies
pip install -r requirements.txt

# Run Django migrations
python manage.py migrate

# Start the Django development server
python manage.py runserver 0.0.0.0:3000

python manage.py collectstatic --noinput