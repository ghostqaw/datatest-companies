# Use official Python image as a base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install required packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port if needed (for your bot, this might not be required)
# EXPOSE 8080

# Define environment variables (optional, if required by the bot)
# ENV TELEGRAM_TOKEN=<your-bot-token>

# Command to run the bot
CMD ["python", "data-tg-bot.py"]
