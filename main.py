import os
import time
import logging
from threading import Thread
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)

# Replace these values with your own
CLIENT_SECRET_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/youtube']
VIDEO_ID = '69Bc2dene40'  # Replace with your live stream video ID
COMMENT_TEXT = '/join bunalume 913674679'  # The comment you want to send
INTERVAL = 60  # Interval in seconds between messages

# Create Flow instance
flow = Flow.from_client_secrets_file(
    CLIENT_SECRET_FILE,
    scopes=SCOPES,
    redirect_uri='https://ffc49be1-c58e-4161-a504-2aa36ecb94c7-00-1b0dxw056nq44.janeway.replit.dev/oauth2callback'
)

@app.route('/')
def index():
    """Redirect to Google's OAuth 2.0 authorization URL."""
    authorization_url, state = flow.authorization_url(
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

    return 'Authorization complete. Message sending loop has started. Check the console for logs.'

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
    logging.info("Starting Flask application")
    app.run(host='0.0.0.0', port=5000, debug=True)