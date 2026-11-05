
import json
import threading
import paho.mqtt.client as mqtt

from flask import Flask, jsonify

app = Flask(__name__)

# Store latest sensor readings
sensorData = {
    "temperature": 0,
    "humidity": 0
}

# Create MQTT client
client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

# Connect to MQTT broker
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT Broker")

        client.subscribe("esp32/sensor")
    else:
        print("MQTT connection failed:", reason_code)


def on_message(client, userdata, msg):
    global sensorData

    try:
        sensorData = json.loads(msg.payload.decode())

        print("Received:", sensorData)

    except json.JSONDecodeError:
        print("Invalid sensor data")


client.on_connect = on_connect
client.on_message = on_message


client.connect("broker.emqx.io", 1883, 60)

@app.route('/api/sensor-data', methods=['GET'])
def get_sensor_data():
    return jsonify(sensorData)


if __name__ == '__main__':

    threading.Thread(
        target=client.loop_forever,
        daemon=True
    ).start()

    app.run(port=3000, debug=False)
