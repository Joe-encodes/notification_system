# 1. Start with a clean, small Python image
FROM python:3.11-slim

# 2. Set environment variables to improve performance
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set the working directory inside the container
WORKDIR /usr/src/app

# 4. Copy the list of dependencies and install them
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy all our project code into the container
COPY . /usr/src/app/

# 6. Expose the port Django will run on
EXPOSE 8000

# 7. The default command to run the Django web server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]