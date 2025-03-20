from flask import Flask, render_template, request, redirect, url_for, jsonify
import json

from dotenv import load_dotenv
import os

# Gemini imports
from google import genai
from google.genai import types
# ElevenLabs imports
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from io import BytesIO
import base64
# Chat imports
import logging
from google.genai.types import Content  # Import the correct type

logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
story_instruct="You are historian and you have to write a story about what the users says. You can start the story with 'Once upon a time, there was a' and then continue the story with the user's input. You can end the story with 'The end'. Write the story in only 50 words."
gemini_api_key = os.getenv('GEMINI_API_KEY')
gemini_client = genai.Client(api_key=gemini_api_key)

elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
elevenlabs_client = ElevenLabs(
  api_key=elevenlabs_api_key,
)



app = Flask(__name__)

def generate_story(prompt):
    response = gemini_client.models.generate_content(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(system_instruction=story_instruct),
    contents=[prompt]
    )
    return response.text

def generate_story_audio(story):
    audio = elevenlabs_client.text_to_speech.convert(
    text=story,
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
    )
    audio_data = BytesIO()
    for chunk in audio:
        audio_data.write(chunk)
    
    return base64.b64encode(audio_data.getvalue()).decode("utf-8") 

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/storyteller', methods=['GET', 'POST'])
def storyterller():
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        response = generate_story(prompt)
        # audio = generate_story_audio(response)
        if response:
            # Generate Base64 audio to embed in HTML
            # audio_base64 = generate_story_audio(audio)
            # return render_template('storyteller.html', response=response, audio=audio_base64)
            return render_template('storyteller.html', response=response)

    return render_template('storyteller.html')

quiz_instruct = """You are a quiz master and you have to generate a quiz based on 
the user's input. Make 5 questions based on the user's input. 
The questions should be of medium difficulty. Each question should have 4 options. 
The correct answer should be one of the options. 
The quiz should be based on the user's input. Return the quiz in JSON format.

Use this JSON schema:

{    
'question': str
'a': str
'b': str
'c': str
'd': str
'correct': str
},
{
'question': str
'a': str
'b': str
'c': str
'd': str
'correct': str
},
{
'question': str
'a': str
'b': str
'c': str
'd': str
'correct': str
},
{
'question': str
'a': str
'b': str
'c': str
'd': str
'correct': str
},
{
'question': str
'a': str
'b': str
'c': str
'd': str
'correct': str
}

Return: list[quiz]

don't use ```json, just return the raw JSON object.
"""
def generate_quiz(topic):
    response = gemini_client.models.generate_content(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(system_instruction=quiz_instruct),
    contents=[topic]
    )
    print(response.text)
    response = response.text.replace("```json", "")
    response = response.replace("```", "")
    return json.loads(response)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        topic = request.form.get('topic')
        quiz_data = generate_quiz(topic)    
        if "```json" in quiz_data:
            # remove the ```json from the response
            quiz_data = quiz_data.replace("```json", "")
            quiz_data = quiz_data.replace("```", "")

        if quiz_data:
            return render_template('quiz.html', quiz_data=(quiz_data))
    return render_template('quiz.html')

chat_instruct = """You are a helpful chatbot. Respond to the user's questions or statements in a conversational manner.
Maintain context throughout the conversation. But keep the conversation only related to histroy. if the user asks about any other topic, bring back the conversation to history.
"""

chat_history = []  # Store conversation history

def generate_chat_response(user_input):
    global chat_history
    chat_history.append(Content(parts=[{"text": user_input}], role="user"))

    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=chat_instruct),
        contents=chat_history
    )

    if response.text: # check if text exists
        bot_response = response.text
        chat_history.append(Content(parts=[{"text": bot_response}], role="model"))
        return bot_response
    else:
        return "Sorry, I couldn't generate a response."

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_input = request.form.get('user_input')
        if user_input:
            bot_response = generate_chat_response(user_input)
            return render_template('chat.html', user_input=user_input, bot_response=bot_response, chat_history=chat_history)
    return render_template('chat.html', chat_history=chat_history)

if __name__ == '__main__':
    app.run(debug=True)