const express = require('express');
const mqtt = require('mqtt');

const app = express();

app.use(express.static('public'));

let sensorData = {
    temperature: 0,
    humidity: 0
};

const client = mqtt.connect('mqtt://broker.emqx.io:1883');

client.on('connect', () => {
    console.log('Connected to MQTT Broker');

    client.subscribe('esp32/sensor');
});

client.on('message', (topic, message) => {
    try {
        sensorData = JSON.parse(message.toString());

        console.log('Received:', sensorData);
    } catch (error) {
        console.log('Invalid sensor data');
    }
});

app.get('/api/sensor-data', (req, res) => {
    res.json(sensorData);
});

app.listen(3000, () => {
    console.log('Server running at http://localhost:3000');
});