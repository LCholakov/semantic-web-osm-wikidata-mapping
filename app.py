from flask import Flask, redirect, request, session
from requests_oauthlib import OAuth2Session
import os
from dotenv import load_dotenv
import logging
import json

logging.basicConfig(level=logging.DEBUG)
load_dotenv()
# ——— CONFIG ———
CLIENT_ID     = os.getenv("OSM_CLIENT_ID")
CLIENT_SECRET = os.getenv("OSM_CLIENT_SECRET")
AUTH_URL      = "https://www.openstreetmap.org/oauth2/authorize"
TOKEN_URL     = "https://www.openstreetmap.org/oauth2/token"
REDIRECT_URI  = "https://127.0.0.1:5678/callback"   # must match exactly in your OSM app settings

# ——— FLASK SETUP ———
app = Flask(__name__)
app.secret_key = os.urandom(24)   # must be set before you use session

@app.route("/")
def index():
    osm = OAuth2Session(
        CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=["write_api"]
    )
    auth_url, state = osm.authorization_url(AUTH_URL)
    # persist state in the user’s session cookie
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route("/callback")
def callback():
    # re-create the session *with* the saved state
    osm = OAuth2Session(
        CLIENT_ID,
        state=session.get('oauth_state'),
        redirect_uri=REDIRECT_URI
    )
    # exchange code + state (from request.url) for token
    token = osm.fetch_token(
        TOKEN_URL,
        client_secret=CLIENT_SECRET,
        authorization_response=request.url
    )
    with open("osm_token.json", "w") as f:
        json.dump(token, f)
    return f"<h2>Access Token</h2><pre>{token}</pre>"

if __name__ == "__main__":
    # if you’re using a self-signed cert, generate cert.pem + key.pem in this directory
    app.run(
      host="0.0.0.0",
      port=5678,
      ssl_context=('cert.pem','key.pem'),  # comment out if you’re using ngrok instead
      debug=True
    )