# gemini-telegram-bot
A Telegram bot powered by Google's Gemini Generative AI model.
## Key Features
* Capable of continuing the previous conversation
* Capable of prompting with an image
* Streams the response
* Formatted responses
## Setup
Create a Docker environment file with the following minimum content:
```
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
GOOGLE_AI_API_KEY=YOUR_GOOGLE_AI_API_KEY
```
Please refer to the `docker-compose.yml` file for additional environment variables.

## Run
```
docker-compose --env-file PATH_TO_YOUR_ENV_FILE up --build 
```
  
