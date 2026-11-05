
import os
import json
import threading
import pandas as pd
import paho.mqtt.client as mqtt

from flask import Flask, jsonify
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

app = Flask(__name__)

# Train the ML model
df = pd.read_csv("logistic_data.csv")

X = df[['Hours_Studied', 'Attendance']]
y = df['Pass']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.1, random_state=42
)

model = LogisticRegression()
model.fit(X_train, y_train)

print("ML model trained successfully!")

# Shared prediction storage
RESULT_FILE = "/tmp/latest_result.json"

latest_result = {"message": "Waiting for student data"}

result_lock = threading.Lock()


# MQTT configuration
BROKER = "broker.emqx.io"
PORT = 1883

INPUT_TOPIC = "student/prediction/input"
OUTPUT_TOPIC = "student/prediction/output"


# MQTT connection callback
def on_connect(client, userdata, flags, reason_code, properties):
    print("MQTT connection status:", reason_code)

    if reason_code == 0:
        client.subscribe(INPUT_TOPIC)
        print("Subscribed to:", INPUT_TOPIC)


# MQTT message callback
def on_message(client, userdata, msg):
    global latest_result

    try:
        data = json.loads(msg.payload.decode())

        hours = float(data['Hours_Studied'])
        attendance = float(data['Attendance'])

        input_data = pd.DataFrame([{
            'Hours_Studied': hours,
            'Attendance': attendance
        }])

        prediction = int(model.predict(input_data)[0])

        result = {
            "Hours_Studied": hours,
            "Attendance": attendance,
            "Prediction": prediction,
            "Result": "Pass" if prediction == 1 else "Fail"
        }

        # Update shared result
        with result_lock:
            latest_result = result

            with open(RESULT_FILE, "w") as f:
                json.dump(result, f)

        print("Prediction received and saved:", result)

        # Publish prediction to MQTT output topic
        client.publish(
            OUTPUT_TOPIC,
            json.dumps(result)
        )

        print("Published result to:", OUTPUT_TOPIC)

    except Exception as e:
        print("Prediction error:", e)


# Create MQTT client
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="student_ml_render_backend"
)

client.on_connect = on_connect
client.on_message = on_message


# Start MQTT connection
def start_mqtt():
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        print("MQTT client started successfully")

    except Exception as e:
        print("MQTT startup error:", e)


# Start MQTT in background
threading.Thread(
    target=start_mqtt,
    daemon=True
).start()


# Dashboard
@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Student Pass Prediction</title>

        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f1f5f9;
                text-align: center;
                padding: 50px;
            }

            .card {
                background: white;
                padding: 30px;
                border-radius: 15px;
                max-width: 450px;
                margin: auto;
                box-shadow: 0 4px 15px #ccc;
            }

            h1 {
                color: #2563eb;
            }

            .result {
                font-size: 24px;
                font-weight: bold;
                margin: 20px;
            }
        </style>
    </head>

    <body>

        <div class="card">

            <h1>Student Pass Prediction</h1>

            <p>Logistic Regression + MQTT</p>

            <h3>Latest Student Details</h3>

            <p id="hours">Hours Studied: Waiting...</p>

            <p id="attendance">Attendance: Waiting...</p>

            <h3>Prediction Result</h3>

            <div class="result" id="result">
                Waiting for student data...
            </div>

            <p id="status">Connecting to MQTT Model...</p>

        </div>

        <script>

            async function updateResult() {

                try {

                    const response = await fetch('/api/result');

                    const data = await response.json();

                    if (data.Result) {

                        document.getElementById('hours').innerText =
                            'Hours Studied: ' + data.Hours_Studied;

                        document.getElementById('attendance').innerText =
                            'Attendance: ' + data.Attendance + '%';

                        document.getElementById('result').innerText =
                            data.Result;

                        document.getElementById('status').innerText =
                            'Prediction updated successfully';

                    } else {

                        document.getElementById('status').innerText =
                            'Waiting for MQTT data...';

                    }

                } catch (error) {

                    document.getElementById('status').innerText =
                        'Unable to fetch prediction';

                }

            }

            updateResult();

            setInterval(updateResult, 2000);

        </script>

    </body>
    </html>
    """


# API to get latest prediction
@app.route("/api/result")
def get_result():

    global latest_result

    try:

        with result_lock:

            if os.path.exists(RESULT_FILE):

                with open(RESULT_FILE, "r") as f:
                    latest_result = json.load(f)

            return jsonify(latest_result)

    except Exception as e:

        print("API error:", e)

        return jsonify({
            "message": "Unable to retrieve prediction"
        }), 500


# Health check
@app.route("/health")
def health():

    return jsonify({
        "status": "running",
        "model": "Logistic Regression",
        "mqtt": "configured"
    })


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 3000))

    app.run(
        host="0.0.0.0",
        port=port
    )
