import cv2
import random
from deepface import DeepFace

# Compliment list
compliments = [
    "You're doing amazing!",
    "You look awesome today!",
    "Keep smiling, it suits you!",
    "You're stronger than you know!",
    "Believe in yourself!",
    "You’re a ray of sunshine!"
]

# Start webcam
cap = cv2.VideoCapture(0)

print("Loading Compliment Mirror... Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Flip the frame like a mirror
    frame = cv2.flip(frame, 1)

    # Analyze only every few frames for performance (optional)
    try:
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        emotion = result[0]['dominant_emotion']

        # If emotion is sad/tired/angry, show a compliment
        if emotion in ['sad', 'angry', 'fear', 'disgust']:
            compliment = random.choice(compliments)
            cv2.putText(frame, compliment, (30, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 255, 0), 2, cv2.LINE_AA)

        # Display detected emotion
        cv2.putText(frame, f"Emotion: {emotion}", (30, 450), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2, cv2.LINE_AA)
    except Exception as e:
        print("Error detecting emotion:", str(e))

    # Show webcam
    cv2.imshow("Compliment Mirror", frame)

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release camera and close windows
cap.release()
cv2.destroyAllWindows()
