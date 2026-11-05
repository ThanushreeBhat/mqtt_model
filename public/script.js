async function getSensorData() {
    try {
        const response = await fetch('/api/sensor-data');
        const data = await response.json();

        document.getElementById('temperature').innerText =
            data.temperature + ' °C';

        document.getElementById('humidity').innerText =
            data.humidity + ' %';

        document.getElementById('status').innerText =
            'Connected to backend';
  
    } catch (error) {
        document.getElementById('status').innerText =
            'Backend connection failed';
    }
}

setInterval(getSensorData, 1000);

getSensorData();