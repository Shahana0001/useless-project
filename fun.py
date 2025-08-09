import cv2
import pyttsx3
import random
import threading
from fer import FER
import time
import queue
import numpy as np
import speech_recognition as sr

# Global flags to signal the main loop and threads
exit_program_flag = threading.Event()
thanked_by_voice = threading.Event()

# Audio Manager with repeat functionality
class AudioManager:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.running = True
        self.worker_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.worker_thread.start()

    def _audio_worker(self):
        while self.running:
            try:
                text = self.audio_queue.get(timeout=1)
                if text:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 170)
                    engine.setProperty('volume', 1.0)
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                    del engine
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Audio Error] {e}")

    def speak(self, text):
        try:
            self.audio_queue.put_nowait(text)
        except queue.Full:
            print("Audio queue full, skipping...")

    def repeat_until_thanked(self, text, stop_flag):
        def repeater():
            while not stop_flag.is_set():
                self.speak(text)
                time.sleep(5)
        threading.Thread(target=repeater, daemon=True).start()

    def stop(self):
        self.running = False

# Compliments database (simplified for clarity)
compliment_db = {
    'happy': [
        "What a great smile!",
        "You look so happy today!",
        "Your joy is contagious!"
    ],
    'sad': [
        "It's okay to feel that way.",
        "Hang in there, you're strong.",
        "You are so loved."
    ],
    'angry': [
        "You have a strong passion!",
        "Your focus is incredible!",
        "You've got this!"
    ],
    'surprise': [
        "That's a fun surprise!",
        "Wow, that's a cool reaction!",
        "You make every moment special!"
    ],
    'fear': [
        "You are so brave!",
        "I believe in you!",
        "Facing fear takes courage."
    ],
    'neutral': [
        "You look so calm and collected.",
        "Your presence is calming.",
        "What a nice, peaceful expression."
    ],
    'disgust': [
        "You have great taste.",
        "That look says it all!",
        "You know what you like, and that's cool."
    ]
}

def get_compliment(emotion):
    return random.choice(compliment_db.get(emotion, ["You are a truly amazing person!"]))

def draw_simple_ui(frame, thanked, active_compliment):
    darkened_frame = cv2.addWeighted(frame, 0.5, np.zeros_like(frame), 0.5, 0)
    overlay = darkened_frame.copy()

    font = cv2.FONT_HERSHEY_TRIPLEX
    color = (255, 255, 255)
    thickness = 1
    font_scale = 0.7
    line_type = cv2.LINE_AA

    if thanked:
        text = "YOU'RE WELCOME!"
    elif active_compliment:
        text = "COMPLIMENTING..."
    else:
        text = "ANALYZING..."

    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = (frame.shape[1] - text_size[0]) // 2
    y = (frame.shape[0] + text_size[1]) // 2

    cv2.putText(overlay, text, (x, y), font, font_scale, color, thickness, line_type)

    # Add a small hint at the bottom
    hint_text = "Say 'thank you' to exit, or press 'q'."
    hint_size, _ = cv2.getTextSize(hint_text, cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, 1)
    hint_x = (frame.shape[1] - hint_size[0]) // 2
    hint_y = frame.shape[0] - 15
    cv2.putText(overlay, hint_text, (hint_x, hint_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, (150,150,150), 1, line_type)

    frame[:] = overlay

# New function for speech recognition
def audio_listener():
    r = sr.Recognizer()
    while not exit_program_flag.is_set():
        with sr.Microphone() as source:
            print("[Speech] Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1)
            print("[Speech] Listening for 'thank you'...")
            try:
                audio = r.listen(source, phrase_time_limit=4)
                text = r.recognize_google(audio).lower()
                print(f"[Speech] Heard: {text}")
                if "thank you" in text:
                    thanked_by_voice.set()
                    break
            except sr.UnknownValueError:
                print("[Speech] Could not understand audio, listening again...")
            except sr.RequestError as e:
                print(f"[Speech] Could not request results from Google Speech Recognition service; {e}")

# ===============================================
# Main Loop for Audio-Only Tracking
# ===============================================

def main():
    fer_detector = FER(mtcnn=True)
    audio_manager = AudioManager()
    compliment_stop_flag = threading.Event()

    current_emotion = ""
    active_compliment = False
    last_compliment_time = 0
    thanked = False
    last_detection_time = time.time()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Webcam not found. Is it being used by another app?")
        return
    cv2.namedWindow("BACKGROUND EMOTION TRACKER", cv2.WINDOW_NORMAL)

    # Start the speech listener thread
    audio_thread = threading.Thread(target=audio_listener, daemon=True)
    audio_thread.start()

    print("[INFO] Program running in background. Audio compliments will be given.")
    print("[INFO] Say 'thank you' to make the program respond and quit.")
    print("[INFO] Press 'q' on the video window to quit the program.")

    while not exit_program_flag.is_set():
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Frame not received.")
            break

        frame = cv2.flip(frame, 1)
        key = cv2.waitKey(1) & 0xFF

        # Check for voice command
        if thanked_by_voice.is_set():
            active_compliment = False
            thanked = True
            compliment_stop_flag.set()
            audio_manager.speak("You're very welcome!")
            time.sleep(2)
            exit_program_flag.set()

        # Emotion detection logic
        if time.time() - last_detection_time > 3 or not active_compliment:
            try:
                result = fer_detector.detect_emotions(frame.copy())
                
                if result:
                    emotions = result[0]['emotions']
                    new_emotion = max(emotions, key=emotions.get)
                    confidence = emotions[new_emotion]
                    current_time = time.time()

                    if (new_emotion != current_emotion or not active_compliment) and \
                       (current_time - last_compliment_time > 5) and confidence > 0.6:

                        compliment_stop_flag.set()
                        compliment_stop_flag.clear()
                        current_emotion = new_emotion
                        current_compliment = get_compliment(current_emotion)
                        active_compliment = True
                        last_compliment_time = current_time

                        print(f"[Emotion] {current_emotion} with confidence: {confidence:.2f}")
                        audio_manager.repeat_until_thanked(current_compliment, compliment_stop_flag)
                else:
                    current_emotion = ""
                    active_compliment = False
                    compliment_stop_flag.set()
            
            except Exception as e:
                print(f"[Detection Error] {e}")
            
            last_detection_time = time.time()
            thanked = False

        if key == ord('q'):
            exit_program_flag.set()
            compliment_stop_flag.set()
            audio_manager.speak("Stay awesome, champion!")
            time.sleep(2)
        
        draw_simple_ui(frame, thanked, active_compliment)
        cv2.imshow("BACKGROUND EMOTION TRACKER", frame)

    audio_manager.stop()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()