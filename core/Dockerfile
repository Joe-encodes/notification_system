# 1. Start with a clean, small Python image
FROM python:3.11-slim

# 2. Set environment variables to improve performance
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set the working directory inside the container
WORKDIR /usr/src/app

# 3.5. Install system dependencies for building Python packages
# This is crucial for packages like cryptography and cffi
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    # Clean up apt lists to reduce image size
    && rm -rf /var/lib/apt/lists/*

# 4. Copy the list of dependencies and install them
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy all our project code into the container
COPY . /usr/src/app/

# 6. Expose the port Django will run on
EXPOSE 8000

# 7. The default command to run the Django web server
# Use the absolute path to the gunicorn executable
CMD ["/usr/local/bin/gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]
