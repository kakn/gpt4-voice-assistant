# gpt4-voice-assistant
This is a proof-of-concept project that captures short snippets of audio, transcribes them using Google Cloud Speech-to-Text, and sends the result to GPT-4 via OpenAI’s API for a real-time, intelligent response.

It was built before voice capabilities were added to tools like ChatGPT, as a personal experiment to explore what a voice assistant powered by a large language model might feel like, inspired by sci-fi AIs. This is in contrast to the reality of voice assistants like Siri or Alexa, which rely on fixed commands and limited dialogue trees.

## Implementation
- Listens to audio output (or microphone input) and captures audio in short segments  
- Transcribes recent audio using Google Cloud Speech-to-Text  
- Once a question or input is detected, sends it as a query to GPT-4  
- Streams GPT-4’s response back in real-time to the terminal  
- GPT-4 is optionally provided with context on the current topic for more relevant responses