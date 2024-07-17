# Use the official Python base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Java
RUN apt-get update && apt-get install -y default-jre

# Copy the rest of the application code into the container
COPY . .

# Specify the command to run on container start
CMD ["python", "main.py"]

