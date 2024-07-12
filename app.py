import os
import pathlib

import requests
from flask import Flask, session, abort, redirect, request, render_template
import math
import mysql.connector
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
    r_string=y_pred[0]
    save_to_db(str(session['name']), int_features, str(r_string))

    return render_template("heart_pred.html" ,prediction=f'Prediction : {y_pred[0]}')



def save_to_db(user_email,features, p_result):
    # Establish the connection
    connection = mysql.connector.connect(
        host='localhost',  # Hostname of the MySQL server
        user='root',  # Your MySQL username
        database='heart_db'  # Name of the database you want to connect to
    )

    # Create a cursor object
    cursor = connection.cursor()

    # Insert into MySQL table
    cursor = connection.cursor()
    insert_query = """
        INSERT INTO prediction_history 
        (gender, age, education, current_smoker, cigs_per_day, BP_meds, prevalent_stroke, prevalent_hyp, diabetes, 
         tot_chol, sys_BP, dia_BP, BMI, heart_rate, glucose, predicted_value,user_email)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)
    """
    cursor.execute(insert_query, (*features, p_result,str(user_email),))

    # Commit the transaction
    connection.commit()

    # Close the cursor and connection
    cursor.close()
    connection.close()




@app.route("/history")
def history():
    # Establish the connection
    connection = mysql.connector.connect(
        host='localhost',  # Hostname of the MySQL server
        user='root',  # Your MySQL username
        database='heart_db'  # Name of the database you want to connect to
    )

    # Create a cursor object
    cursor = connection.cursor()

    # Execute a query (corrected to use proper string formatting)
    user_email = session['name']
    query = f"SELECT * FROM prediction_history  WHERE user_email = '{user_email}'"
    cursor.execute(query)
    # Fetch the results
    results = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    connection.close()

    return render_template("History.html", results=results, User='Hi, {}'.format(session['name']))









if __name__ == "__main__":
    app.run(debug=True)
