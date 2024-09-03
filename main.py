import os
import json
import time
import logging
from threading import Thread
from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)

# Replace these values with your own
SCOPES = ['https://www.googleapis.com/auth/youtube']
VIDEO_ID = os.environ.get('VIDEO_ID', '69Bc2dene40')  # Replace with your live stream video ID
COMMENT_TEXT = os.environ.get('COMMENT_TEXT', '/join bunalume 913674679')  # The comment you want to send
INTERVAL = int(os.environ.get('INTERVAL', 45))  # Interval in seconds between messages

# Use environment variables for sensitive information
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI')

# Create Flow instance
try:
    client_config = json.loads(CLIENT_SECRET)
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
except json.JSONDecodeError:
    logging.error("Failed to parse CLIENT_SECRET. Make sure it's a valid JSON string.")
    flow = None
except Exception as e:
    logging.error(f"Error creating Flow: {str(e)}")
    flow = None

@app.route('/')
def index():
    """Redirect to Google's OAuth 2.0 authorization URL."""
    if not flow:
        return "Error: OAuth flow not initialized correctly", 500
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    logging.info(f"Authorization URL generated: {authorization_url}")
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth 2.0 callback and exchange the authorization code for credentials."""
    logging.info("Received OAuth callback")
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    logging.info("Credentials obtained successfully")
    
    # Start the message sending loop in a separate thread
    thread = Thread(target=message_loop, args=(creds,))
    thread.start()
    logging.info("Message sending thread started")
    
    return 'Authorization complete. Message sending loop has started. Check the logs for details.'

def message_loop(creds):
    """Continuously send messages at regular intervals."""
    youtube = build('youtube', 'v3', credentials=creds)
    try:
        live_chat_id = get_live_chat_id(youtube, VIDEO_ID)
        logging.info(f'Live Chat ID obtained: {live_chat_id}')
        
        while True:
            try:
                response = send_message(youtube, live_chat_id, COMMENT_TEXT)
                logging.info(f'Message sent successfully: {response}')
            except HttpError as e:
                logging.error(f'An error occurred while sending the message: {e}')
            
            logging.info(f'Waiting for {INTERVAL} seconds before sending the next message')
            time.sleep(INTERVAL)
    except HttpError as e:
        logging.error(f'An error occurred while getting the live chat ID: {e}')

def get_live_chat_id(youtube, video_id):
    """Retrieve the live chat ID from the video."""
    logging.info(f'Attempting to get live chat ID for video: {video_id}')
    request = youtube.videos().list(
        part='liveStreamingDetails',
        id=video_id
    )
    response = request.execute()
    logging.info(f'Video details response: {response}')
    live_chat_id = response['items'][0]['liveStreamingDetails']['activeLiveChatId']
    return live_chat_id

def send_message(youtube, live_chat_id, message):
    """Send a message to the live chat."""
    logging.info(f'Attempting to send message: "{message}" to chat ID: {live_chat_id}')
    request = youtube.liveChatMessages().insert(
        part='snippet',
        body={
            'snippet': {
                'liveChatId': live_chat_id,
                'type': 'textMessageEvent',
                'textMessageDetails': {
                    'messageText': message
                }
            }
        }
    )
    response = request.execute()
    return response

if __name__ == '__main__':
    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
