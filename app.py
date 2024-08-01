import ssl
import requests

# Disable SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context

import os
import json
from flask import Flask, request, render_template, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, CouldNotRetrieveTranscript
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv('dev.env')
gemini_api_key = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)

def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("=")[1]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)

        transcript = ""
        for i in transcript_text:
            transcript += " " + i["text"]

        return transcript
    except NoTranscriptFound:
        return "Transcript not found for this video."
    except CouldNotRetrieveTranscript:
        return "Could not retrieve the transcript."
    except Exception as e:
        raise e

def final_json(youtube_url):
    youtube_text = extract_transcript_details(youtube_url)

    # Configure the Gemini API
    genai.configure(api_key=gemini_api_key)
    
    # Create a GenerativeModel instance
    model = genai.GenerativeModel('gemini-pro')
   
    system_content = '''You are a great cooking Expert. You will be given a youtube transcript and you need to find the key features like time taken for recipe, list of ingredients, name of recipe and instructions to cook.
                You need to output a JSON with keys name, ingredients and instructions.
                You need to give a parsable JSON without any extra terms.
'''
    user_content = f'''Youtube_transcript: {youtube_text}
                    You need to give a JSON with keys name of the recipe, ingredients and detailed instructions for making the recipe.
                     The output should be a direct dictionary without any text outside.'''
    
    try:
        # Use the model to generate content
        response = model.generate_content([system_content, user_content])
        
        # Extract the generated text
        result_final = response.text
    
        result_json = json.loads(result_final)
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

    return result_json

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        youtube_url = request.form['youtube_url']
        try:
            result = final_json(youtube_url)
            return render_template('index.html', result=result)
        except Exception as e:
            return render_template('index.html', error=str(e))
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    youtube_url = data.get('youtube_url')
    if not youtube_url:
        return jsonify({'error': 'No YouTube URL provided'}), 400
    
    try:
        result = final_json(youtube_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
