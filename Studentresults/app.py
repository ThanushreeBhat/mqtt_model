
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

# Store latest prediction
latest_result = {"message": "Waiting for student data"}

# MQTT configuration
BROKER = "broker.emqx.io"
PORT = 1883
INPUT_TOPIC = "student/prediction/input"
OUTPUT_TOPIC = "student/prediction/output"


def on_connect(client, userdata, flags, reason_code, properties):
    print("MQTT connection status:", reason_code)

    if reason_code == 0:
        client.subscribe(INPUT_TOPIC)
        print("Subscribed to:", INPUT_TOPIC)


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

        latest_result = {
            "Hours_Studied": hours,
            "Attendance": attendance,
            "Prediction": prediction,
            "Result": "Pass" if prediction == 1 else "Fail"
        }

        print("Prediction:", latest_result)

        client.publish(
            OUTPUT_TOPIC,
            json.dumps(latest_result)
        )

    except Exception as e:
        print("Prediction error:", e)


# Create MQTT client
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="student_ml_render_backend"
)

client.on_connect = on_connect
client.on_message = on_message


def start_mqtt():
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
    except Exception as e:
        print("MQTT startup error:", e)


# Start MQTT in background
threading.Thread(target=start_mqtt, daemon=True).start()


# Public URL home page
@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Student Pass Prediction</title>
        <style>
            body {
                font-family: Arial;
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
            h1 { color: #2563eb; }
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
            <p id="status">MQTT Model Active</p>
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



@app.route("/api/result")
def get_result():
    return jsonify(latest_result)


@app.route("/health")
def health():
    return jsonify({"status": "running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
