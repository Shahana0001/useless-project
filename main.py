import cv2
import pyttsx3
import random
import threading
from fer import FER
import time

# Initialize camera
cap = cv2.VideoCapture(0)

# Initialize FER detector
detector = FER(mtcnn=True)

# Text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 160)
engine.setProperty('volume', 1.0)

# Compliments database
compliments = {
    'happy': [
        "That smile is brighter than the sun!",
        "You're glowing with happiness!",
        "Keep smiling, it suits you!"
    ],
    'sad': [
        "You're strong, even on tough days.",
        "This moment will pass, you're amazing.",
        "You're not alone. You're doing great."
    ],
    'angry': [
        "Take a deep breath, you're powerful.",
        "Your passion is inspiring!",
        "Even in anger, you shine!"
    ],
    'surprise': [
        "You look amazed, and it's adorable!",
        "Wow! That reaction is priceless.",
        "Curiosity looks great on you!"
    ],
    'fear': [
        "Courage starts with showing up.",
        "You're brave even when scared.",
        "Fear means you're trying something new!"
    ],
    'disgust': [
        "Your standards are top-notch!",
        "That face means you're real!",
        "You know what's best, always."
    ],
    'neutral': [
        "Calm and cool – that's style!",
        "You're looking sharp today.",
        "Effortlessly confident – nice!"
    ]
}

# Globals
last_emotion = None
repeat_thread = None
stop_repeat = threading.Event()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def repeat_compliment(compliment):
    while not stop_repeat.is_set():
        speak(compliment)
        time.sleep(5)

print("[INFO] Press 't' to say 'Thank you' and stop the audio.")
print("[INFO] Press 'q' to quit the program.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detect emotion
    result = detector.detect_emotions(frame)
    if result:
        emotions = result[0]["emotions"]
        top_emotion = max(emotions, key=emotions.get)
        confidence = emotions[top_emotion]

        # Display emotion on screen
        cv2.putText(frame, f"Emotion: {top_emotion} ({confidence:.2f})", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if top_emotion != last_emotion and confidence > 0.6:
            last_emotion = top_emotion
            compliment = random.choice(compliments.get(top_emotion, ["You're amazing!"]))
            stop_repeat.clear()
            if repeat_thread and repeat_thread.is_alive():
                stop_repeat.set()
                repeat_thread.join()
            stop_repeat.clear()
            repeat_thread = threading.Thread(target=repeat_compliment, args=(compliment,), daemon=True)
            repeat_thread.start()

    cv2.imshow("Compliment Mirror", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        stop_repeat.set()
        break
    elif key == ord('t'):
        print("[INFO] Thank you detected. Stopping compliments.")
        stop_repeat.set()

cap.release()
cv2.destroyAllWindows()
