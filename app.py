# polling process, would be more efficient to switch to webhook system for production, but sandbox doesn't support webhooks (looking into for future)
import os
import sys
import argparse
import threading
import time
from flask import Flask
from dotenv import load_dotenv

# import custom functions
from sms_api import send_messages, fetch_messages
from menu import get_preset, display_menu, display_error
from configfile import load_last_id, save_last_id
from query_data import query_rag

def main():
    # kick off polling process
    t = threading.Thread(target=poll_inbound, daemon=True)
    t.start()

    # launch flask app on port 55000
    app.run(host="0.0.0.0", port=55000)

# logic for processing messages
def handle_inbound(from_number, text):
    stage = sessions.get(from_number, "NEW")

    # start conversation, showing menu and saving session
    if stage == "NEW":
        reply = display_menu(LANG_ID)
        sessions[from_number] = "AWAITING_CHOICE"

    # continue conversation, based on menu choice return response
    elif stage == "AWAITING_CHOICE":
        if text in ("1","2","3","4","5","6","7","8"):
            reply = get_preset(text, LANG_ID)
            sessions.pop(from_number, None)
        elif text == "9":
            # ask user for custom inquiry
            if LANG_ID == 1:
                reply = "Ingiza swali lako maalum:"
            else:
                reply = "Enter your custom question:"
            sessions[from_number] = "AWAITING_INPUT"
        else:
            reply = display_error(0, LANG_ID) + display_menu(LANG_ID)

    # genai response, reply based on users input and received rag output
    elif stage == "AWAITING_INPUT":
        reply = query_rag(text)
        sessions.pop(from_number, None)

    # error case, show menu and set to waiting for response
    else:
        reply = display_menu()
        sessions[from_number] = "AWAITING_CHOICE"

    # based on selected reply above, send user message
    send_messages(USERNAME, API_KEY, [from_number], reply, SENDER_ID)

# threaded process for monitoring incoming messages
def poll_inbound():
    global last_id
    while True:
        try:
            data = fetch_messages(USERNAME, API_KEY, last_id)
            msgs = data.get("SMSMessageData", {}).get("Messages", [])
            for m in msgs:
                handle_inbound(m["from"], m["text"].strip())
                last_id = max(last_id, m["id"])
                save_last_id(last_id)
        except Exception as e:
            print(f"Failed to fetch messages: {e}")
        time.sleep(5)  # currently 5 second wait

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the SMS application in sandbox or production mode")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--sandbox", action="store_true", help="Run in sandbox mode (default)")
    group.add_argument("-p", "--prod", action="store_true", help="Run in production mode")
    args = parser.parse_args()
    
    # Load presets based on environment
    load_dotenv()
    LANG_ID = int(os.getenv("LANG_ID")) # env variable for language: 0 for english, 1 for swahili

    if args.prod:
        print("Running in PRODUCTION mode")
        USERNAME  = os.getenv("AT_USERNAME") # env variable for Africa Talking id name
        API_KEY   = os.getenv("AT_API") # env variable for Africa Talking api key
        SENDER_ID = os.getenv("AT_SEND_ID") # env variable for Africa Talking phone number/shortcode 
    else:
        # default to sandbox
        print("Running in SANDBOX mode")
        USERNAME  = os.getenv("SAND_USERNAME") # env variable for Sandbox id name
        API_KEY   = os.getenv("SAND_API") # env variable for Sandbox api key
        SENDER_ID = os.getenv("SAND_SEND_ID") # env variable for Sandbox phone number/shortcode 

    # flask backend setup
    app = Flask(__name__)
    sessions = {} # temp store convos in here for now (need long term storage?)
    last_id = load_last_id()
    
    # run the main process
    main()
