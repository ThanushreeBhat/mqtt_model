
require('dotenv').config();

const express = require('express');
const mqtt = require('mqtt');

const app = express();

app.use(express.static('public'));

// Broker and server configuration from environment variables
const PORT = process.env.PORT || 3000;
const BROKER_URL = process.env.MQTT_BROKER_URL || 'mqtt://broker.emqx.io:1883';
const TOPIC = process.env.MQTT_TOPIC || 'esp32/sensor';

// In-memory storage for latest sensor readings
let sensorData = {
  temperature: 0,
  humidity: 0
};

// Connect to the MQTT broker
console.log(`Connecting to MQTT broker: ${BROKER_URL}`);
const client = mqtt.connect(BROKER_URL);

// 1. MQTT Connection Event
client.on('connect', () => {
  console.log('Connected to MQTT Broker successfully');

  // Subscribe to the ESP32 sensor topic
  client.subscribe(TOPIC, (err) => {
    if (err) {
      console.error(`Failed to subscribe to topic "${TOPIC}":`, err.message);
    } else {
      console.log(`Subscribed to topic: "${TOPIC}"`);
    }
  });
});

// 2. Handle Incoming MQTT Messages from ESP32
client.on('message', (topic, message) => {
  if (topic === TOPIC) {
    try {
      // Convert raw message buffer to string and parse JSON
      sensorData = JSON.parse(message.toString());

      // Display received sensor data in the backend console
      console.log('ESP32 Data received:', sensorData);
    } catch (error) {
      // Handle invalid JSON payload without crashing the server
      console.error('Invalid JSON received on topic:', topic);
      console.error('Raw message:', message.toString());
    }
  }
});

// 3. Handle MQTT Connection Errors
client.on('error', (err) => {
  console.error('MQTT Connection Error:', err.message);
});

// 4. REST API: Return the latest sensor data in JSON format
app.get('/api/sensor-data', (req, res) => {
  res.json(sensorData);
});

// 5. Start the Express server
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Sensor API endpoint: http://localhost:${PORT}/api/sensor-data`);
});
