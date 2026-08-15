FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app  

# Copy the requirements file into the container
COPY requirements.txt .

# Install build tools (pip, setuptools, wheel) first, then install requirements
# This allows for building/compiling packages that need it
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that the app runs on
EXPOSE 8080

# Run the Mesop application using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "main:me"]