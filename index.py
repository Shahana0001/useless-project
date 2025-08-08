import cv2
import pyttsx3
import random
import threading
from deepface import DeepFace
import time

# Initialize TTS engine
engine = pyttsx3.init()
engine.setProperty('rate', 160)

# Compliment dictionary
compliment_map = {
    'happy': ["You're a ray of sunshine!", "Your joy is contagious!"],
    'sad': ["You are stronger than your emotions.", "It's okay to feel sad sometimes."],
    'angry': ["Calmness is your superpower.", "Take a deep breath, you're doing great."],
    'surprise': ["You always bring the fun!", "You're full of life!"],
    'fear': ["You're braver than you believe.", "Fear fades in the face of courage."],
    'neutral': ["You bring peace wherever you go.", "You're calmly powerful."],
    'disgust': ["You're rising above it all!", "Even tough moments don't define you."]
}

# Shared state flags
emotion_detected = False
user_said_thankyou = False
stop_compliment = False
chosen_emotion = ""
selected_compliment = ""

# Function to speak the compliment in loop
def compliment_loop():
    global stop_compliment
    while not stop_compliment and not user_said_thankyou:
        engine.say(selected_compliment)
        engine.runAndWait()
        time.sleep(2)  # Small delay between repeats

# Open webcam
cap = cv2.VideoCapture(0)
cv2.namedWindow("Compliment Mirror", cv2.WINDOW_NORMAL)

print("Running Compliment Mirror...")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    key = cv2.waitKey(1)

    if not emotion_detected:
        try:
            result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
            chosen_emotion = result[0]['dominant_emotion']
            selected_compliment = random.choice(compliment_map.get(chosen_emotion, ["You're amazing!"]))
            emotion_detected = True
            print("Emotion Detected:", chosen_emotion)

            # Start compliment thread
            threading.Thread(target=compliment_loop, daemon=True).start()

        except Exception as e:
            print("Emotion detection error:", e)

    if emotion_detected and not user_said_thankyou:
        cv2.putText(frame, f"Emotion: {chosen_emotion.capitalize()}", (30, 440),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, selected_compliment, (30, 60),
                    cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 3)
        cv2.putText(frame, 'Press "T" to say Thank You', (30, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)

        if key == ord('t'):
            stop_compliment = True
            user_said_thankyou = True
            time.sleep(0.5)  # Let the current speech finish
            engine.say("You're welcome!")
            engine.runAndWait()

    if user_said_thankyou:
        cv2.putText(frame, "😊 Thank you received!", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)

    if key == ord('q'):
        stop_compliment = True
        break

    cv2.imshow("Compliment Mirror", frame)

cap.release()
cv2.destroyAllWindows()