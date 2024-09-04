FROM python:3.10-slim

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc

# Upgrade pip to the latest version
RUN pip install --upgrade pip

WORKDIR /app
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "data-tg-bot.py"]
