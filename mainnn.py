import cv2
import pyttsx3
import random
import threading
from fer import FER
import time
import numpy as np
import queue

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

# Initialize
audio_manager = AudioManager()
compliment_stop_flag = threading.Event()
fer_detector = FER(mtcnn=True)

compliment_db = {
    'happy': [
        "You're radiating awesomeness!",
        "That smile could power a city!",
        "Your joy is CONTAGIOUS!"
    ],
    'sad': [
        "Your strength is INSPIRING!",
        "Even now, you're INCREDIBLE!",
        "Tough times make CHAMPIONS like you!"
    ],
    'angry': [
        "That passion is NEXT-LEVEL!",
        "Your intensity is ELECTRIFYING!",
        "Leader energy detected!"
    ],
    'surprise': [
        "Best reaction EVER!",
        "You make surprise look COOL!",
        "That expression? ICONIC!"
    ],
    'fear': [
        "Facing fears? That's HERO stuff!",
        "Your courage is SHINING through!",
        "Brave souls like you CHANGE THE WORLD!"
    ],
    'neutral': [
        "Cool, calm, and TOTALLY AWESOME!",
        "That effortless cool? UNMATCHED!",
        "You make ordinary look EXTRAORDINARY!"
    ],
    'disgust': [
        "Your standards? LEGENDARY!",
        "That discerning eye? GENIUS!",
        "You see what others miss - VISIONARY!"
    ]
}

# Globals
current_emotion = ""
current_compliment = ""
active_compliment = False
exit_program = False
last_compliment_time = 0
thanked = False
last_detection_time = time.time()

fonts = [
    cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
    cv2.FONT_HERSHEY_COMPLEX,
    cv2.FONT_HERSHEY_TRIPLEX,
    cv2.FONT_ITALIC
]

def get_compliment(emotion):
    return random.choice(compliment_db.get(emotion, ["You're UNIQUELY AMAZING!"]))

def apply_text_effect(frame, text, position, font_index, color, thickness, shadow=True):
    font_scale = 0.8 + (font_index * 0.2)
    if shadow:
        cv2.putText(frame, text, (position[0]+2, position[1]+2), fonts[font_index], font_scale, (0,0,0), thickness+2)
    cv2.putText(frame, text, position, fonts[font_index], font_scale, color, thickness)

def process_frame(frame):
    global current_emotion, current_compliment, active_compliment, last_compliment_time, compliment_stop_flag

    try:
        # Use FER for emotion detection
        result = fer_detector.detect_emotions(frame)
        if result:
            emotions = result[0]['emotions']
            new_emotion = max(emotions, key=emotions.get)
            confidence = emotions[new_emotion]
            current_time = time.time()

            if (new_emotion != current_emotion or not active_compliment) and \
               (current_time - last_compliment_time > 5) and confidence > 0.6:

                compliment_stop_flag.clear()
                current_emotion = new_emotion
                current_compliment = get_compliment(current_emotion)
                active_compliment = True
                last_compliment_time = current_time

                print(f"[Emotion] {current_emotion} with confidence: {confidence:.2f}")
                audio_manager.repeat_until_thanked(current_compliment, compliment_stop_flag)
        else:
             current_emotion = "" # Reset emotion if no face is detected
             active_compliment = False
             compliment_stop_flag.set() # Stop any running audio

    except Exception as e:
        print(f"[Detection Error] {e}")

def draw_ui(frame, thanked):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0,0), (frame.shape[1], 120), (20,20,60), -1)
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

    if thanked:
        apply_text_effect(frame, "YOU'RE WELCOME SUPERSTAR!", (frame.shape[1]//6, frame.shape[0]//2), 3, (0,255,255), 3)
        apply_text_effect(frame, "Keep being AWESOME!", (frame.shape[1]//4, frame.shape[0]//2 + 50), 1, (255,255,0), 2)
    elif current_compliment and active_compliment:
        apply_text_effect(frame, f"EMOTION: {current_emotion.upper()}", (20, 40), 2, (255,100,100), 2)
        y_pos = 80
        for i, line in enumerate([current_compliment[i:i+30] for i in range(0, len(current_compliment), 30)]):
            apply_text_effect(frame, line, (20, y_pos), i % 3, (100,255,255), 2)
            y_pos += 40

        if int(time.time()*2) % 2 == 0:
            apply_text_effect(frame, "PRESS [T] TO THANK ME", (frame.shape[1]//3, frame.shape[0]-30), 3, (0,255,0), 2)
    else:
        apply_text_effect(frame, "ANALYZING YOUR AWESOMENESS...", (frame.shape[1]//4, frame.shape[0]//2), 0, (255,255,255), 2)

# Video Setup
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[ERROR] Webcam not found. Is it being used by another app?")
    exit()

cv2.namedWindow("AWESOME-O-MATIC 3000", cv2.WINDOW_NORMAL)

# Main Loop
while not exit_program:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Frame not received.")
        break

    frame = cv2.flip(frame, 1)
    key = cv2.waitKey(1) & 0xFF

    if time.time() - last_detection_time > 3 or not active_compliment:
        process_frame(frame.copy())
        last_detection_time = time.time()
        thanked = False

    if key == ord('t') and active_compliment:
        active_compliment = False
        thanked = True
        compliment_stop_flag.set()
        audio_manager.speak("No no, THANK YOU for being amazing!")
        threading.Timer(3.0, lambda: setattr(globals(), 'thanked', False)).start()

    elif key == ord('q'):
        exit_program = True
        compliment_stop_flag.set()
        audio_manager.speak("Stay awesome, champion!")
        time.sleep(2)

    draw_ui(frame, thanked)
    cv2.imshow("AWESOME-O-MATIC 3000", frame)

# Cleanup
audio_manager.stop()
cap.release()
cv2.destroyAllWindows()