import os
import pathlib

import requests
from flask import Flask, session, abort, redirect, request, render_template
import math
import pickle
import numpy as np
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests


app = Flask("Heart disease Prediction")
app.secret_key = "Heart disease Prediction"

model = pickle.load(open('./models/sv_model.pkl','rb'))  # The scaler fitted on the training data

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = "201085600669-pub3ikbrtvic656pv4hho0udg6qjvtbt.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["picture"] = id_info.get("picture")  # Get the profile image URL
    return redirect("/home")




@app.route("/logout")
def logout():
    session.clear()
    return render_template("login.html")


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/home")
@login_is_required
def home():
    return render_template("index.html", User='{}'.format(session['name']))


@app.route("/pred")
def pred():


     if "google_id" not in session:
            return abort(401)  # Authorization required
     else:
            return render_template("heart_pred.html", User='{}'.format(session['name']))
    



@app.route('/prediction_', methods=['POST', 'GET'])
def prediction_():
    int_features = [x for x in request.form.values()]
    int_features = [float(x) for x in int_features]
    print(int_features)
    array_numpy_features = np.array(int_features).reshape(1, -1)

    # Predict using the trained classifier
    y_pred = model.predict(array_numpy_features)
    print("Predicted values for new user input data:", y_pred)

    return render_template("heart_pred.html" ,prediction=f'Prediction : {y_pred[0]}')





if __name__ == "__main__":
    app.run(debug=True)
