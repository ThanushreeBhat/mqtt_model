
import pandas as pd
import json
import paho.mqtt.client as mqtt
from sklearn.model_selection import train_test_split
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

df=pd.read_csv("logistic_data.csv")

X=df[['Hours_Studied','Attendance']]
y=df['Pass']

X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.1,random_state=42)
model=LogisticRegression()
model.fit(X_train,y_train)

BROKER = "broker.emqx.io"
PORT = 1883
INPUT_TOPIC = "student/prediction/input"
OUTPUT_TOPIC = "student/prediction/output"


def on_connect(client, userdata, flags, reason_code, properties):
    print("Connection status:", reason_code)

    if reason_code == 0:
        print("Connected successfully!")
        client.subscribe(INPUT_TOPIC)
        print("Subscribed to:", INPUT_TOPIC)


def on_message(client, userdata, msg):
    print("Message received:", msg.payload.decode())

    try:
        data = json.loads(msg.payload.decode())

        hours = data['Hours_Studied']
        attendance = data['Attendance']

        input_data = pd.DataFrame([{
            'Hours_Studied': hours,
            'Attendance': attendance
        }])

        prediction = model.predict(input_data)[0]

        result = {
            "Hours_Studied": hours,
            "Attendance": attendance,
            "Prediction": int(prediction),
            "Result": "Pass" if prediction == 1 else "Fail"
        }

        print("Sending prediction:", result)

        info = client.publish(OUTPUT_TOPIC, json.dumps(result))
        print("Publish status:", info.rc)

    except Exception as e:
        print("Error:", e)

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

print("Waiting for student data...")

client.loop_forever()

