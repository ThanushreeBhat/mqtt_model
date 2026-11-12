import encodings
import encodings.idna
import codecs

print("ENCODINGS PATH:", encodings.__file__, flush=True)

try:
    print("IDNA TEST:", codecs.lookup("idna"), flush=True)
except Exception as e:
    print("IDNA ERROR:", repr(e), flush=True)
import os
import json
import threading

import pandas as pd
import paho.mqtt.client as mqtt

from flask import Flask, jsonify
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# ==========================================
# 1. FLASK APPLICATION
# ==========================================

app = Flask(__name__)


# ==========================================
# 2. TRAIN ML MODEL
# ==========================================

df = pd.read_csv("logistic_data.csv")

X = df[["Hours_Studied", "Attendance"]]
y = df["Pass"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.1,
    random_state=42
)

model = LogisticRegression()
model.fit(X_train, y_train)

test_predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, test_predictions)

print("ML model trained successfully!")
print("Model accuracy:", accuracy)


# ==========================================
# 3. RESULT STORAGE
# ==========================================

latest_result = {
    "message": "Waiting for ESP32 batch data"
}

result_lock = threading.Lock()


# ==========================================
# 4. MQTT CONFIGURATION
# ==========================================

BROKER = "3.121.120.104"
PORT = 1883

# ESP32 publishes batches here
INPUT_TOPIC = "bhavishya/student/batch"

# Python publishes predictions here
# EC team must subscribe to this topic to receive predictions.
OUTPUT_TOPIC = "bhavishya/student/predictions"


# ==========================================
# 5. MQTT CONNECTION
# ==========================================

def on_connect(client, userdata, flags, reason_code, properties):

    print("MQTT connection status:", reason_code)

    if reason_code == 0:

        client.subscribe(INPUT_TOPIC, qos=1)

        print("Subscribed to:", INPUT_TOPIC)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):

    print("MQTT disconnected:", reason_code)


# ==========================================
# 6. RECEIVE BATCH AND PREDICT
# ==========================================

def on_message(client, userdata, msg):

    global latest_result

    try:

        received_message = msg.payload.decode()

        print("Received ESP32 batch:", received_message)

        # Convert JSON into dictionary
        data = json.loads(received_message)

        # Extract records array
        records = data["records"]

        predictions = []

        # Process every student record
        for index, record in enumerate(records, start=1):

            hours = float(record["Hours_Studied"])
            attendance = float(record["Attendance"])

            # Validate input
            if hours < 0:
                raise ValueError("Hours_Studied cannot be negative")

            if not 0 <= attendance <= 100:
                raise ValueError("Attendance must be between 0 and 100")

            # Prepare model input
            input_data = pd.DataFrame([{
                "Hours_Studied": hours,
                "Attendance": attendance
            }])

            # Predict
            prediction = int(model.predict(input_data)[0])

            # Store individual prediction
            student_result = {
                "Student_Number": index,
                "Hours_Studied": hours,
                "Attendance": attendance,
                "Prediction": prediction,
                "Result": "Pass" if prediction == 1 else "Fail"
            }

            predictions.append(student_result)

        # Prepare complete batch response
        result = {
            "Batch": data.get("batch"),
            "Total_Records": len(predictions),
            "Model": "Logistic Regression",
            "Accuracy": accuracy,
            "Predictions": predictions
        }

        # Update dashboard data
        with result_lock:
            latest_result = result

        print("Batch prediction completed!")
        print(json.dumps(result, indent=4))

        # Publish predictions to a separate topic
        info = client.publish(
            OUTPUT_TOPIC,
            json.dumps(result),
            qos=1
        )

        if info.rc == mqtt.MQTT_ERR_SUCCESS:

            print("Predictions published successfully!")

        else:

            print("MQTT publish failed:", info.rc)

    except Exception as e:

        print("Prediction error:", e)


# ==========================================
# 7. MQTT CLIENT
# ==========================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="student_ml_render_backend"
)

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect


# ==========================================
# 8. START MQTT
# ==========================================

def start_mqtt():

    try:

        print("Connecting to MQTT broker...")

        client.connect(BROKER, PORT, 60)

        client.loop_start()

        print("MQTT client started successfully!")

    except Exception as e:

        print("MQTT startup error:", e)


mqtt_thread = threading.Thread(
    target=start_mqtt,
    daemon=True
)

mqtt_thread.start()


# ==========================================
# 9. FLASK DASHBOARD
# ==========================================

@app.route("/")
def home():

    return """
    <!DOCTYPE html>
    <html>

    <head>

        <title>Student Batch Prediction</title>

        <style>

            body {
                font-family: Arial, sans-serif;
                background: #f1f5f9;
                text-align: center;
                padding: 30px;
            }

            .card {
                background: white;
                padding: 25px;
                border-radius: 15px;
                max-width: 800px;
                margin: auto;
                box-shadow: 0 4px 15px #ccc;
            }

            h1 {
                color: #2563eb;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }

            th, td {
                padding: 10px;
                border: 1px solid #ddd;
            }

            th {
                background: #e2e8f0;
            }

        </style>

    </head>

    <body>

        <div class="card">

            <h1>Student Batch Prediction</h1>

            <p>ESP32 + MQTT + Logistic Regression</p>

            <h3 id="batch">Waiting for ESP32 batch...</h3>

            <p id="count"></p>

            <p id="status">Connecting...</p>

            <table>

                <thead>
                    <tr>
                        <th>Student</th>
                        <th>Hours Studied</th>
                        <th>Attendance</th>
                        <th>Prediction</th>
                    </tr>
                </thead>

                <tbody id="results">
                </tbody>

            </table>

        </div>

        <script>

            async function updateResult() {

                try {

                    const response = await fetch("/api/result");

                    const data = await response.json();

                    if (data.Predictions) {

                        document.getElementById("batch").innerText =
                            "Batch Number: " + data.Batch;

                        document.getElementById("count").innerText =
                            "Total Students: " + data.Total_Records;

                        document.getElementById("status").innerText =
                            "Batch received and predictions completed";

                        const tbody =
                            document.getElementById("results");

                        tbody.innerHTML = "";

                        data.Predictions.forEach(student => {

                            const row = document.createElement("tr");

                            const values = [
                                student.Student_Number,
                                student.Hours_Studied,
                                student.Attendance + "%",
                                student.Result
                            ];

                            values.forEach(value => {

                                const cell = document.createElement("td");

                                cell.textContent = value;

                                row.appendChild(cell);

                            });

                            tbody.appendChild(row);

                        });

                    } else {

                        document.getElementById("status").innerText =
                            "Waiting for ESP32 batch...";

                    }

                } catch (error) {

                    document.getElementById("status").innerText =
                        "Unable to fetch predictions";

                }

            }

            updateResult();

            setInterval(updateResult, 2000);

        </script>

    </body>

    </html>
    """


# ==========================================
# 10. PREDICTION API
# ==========================================

@app.route("/api/result")
def get_result():

    with result_lock:

        return jsonify(latest_result)


# ==========================================
# 11. HEALTH CHECK
# ==========================================

@app.route("/health")
def health():

    return jsonify({
        "status": "running",
        "model": "Logistic Regression",
        "mqtt": "configured",
        "accuracy": accuracy
    })


# ==========================================
# 12. RUN FLASK
# ==========================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 3000))

    app.run(
        host="0.0.0.0",
        port=port
    )
