import cv2
import pyttsx3
import random
import threading
from fer import FER
import time
import queue
import numpy as np

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

# Compliments database
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

def get_compliment(emotion):
    return random.choice(compliment_db.get(emotion, ["You're UNIQUELY AMAZING!"]))

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
    hint_text = "Press 't' to thank, 'q' to quit."
    hint_size, _ = cv2.getTextSize(hint_text, cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, 1)
    hint_x = (frame.shape[1] - hint_size[0]) // 2
    hint_y = frame.shape[0] - 15
    cv2.putText(overlay, hint_text, (hint_x, hint_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, (150,150,150), 1, line_type)

    frame[:] = overlay

# ===============================================
# Main Loop for Audio-Only Tracking
# ===============================================

def main():
    fer_detector = FER(mtcnn=True)
    audio_manager = AudioManager()
    compliment_stop_flag = threading.Event()

    current_emotion = ""
    active_compliment = False
    exit_program = False
    last_compliment_time = 0
    thanked = False
    last_detection_time = time.time()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Webcam not found. Is it being used by another app?")
        return
    cv2.namedWindow("BACKGROUND EMOTION TRACKER", cv2.WINDOW_NORMAL)

    print("[INFO] Program running in background. Audio compliments will be given.")
    print("[INFO] Press 't' to thank the mirror.")
    print("[INFO] Press 'q' to quit the program.")

    while not exit_program:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Frame not received.")
            break

        frame = cv2.flip(frame, 1)
        key = cv2.waitKey(1) & 0xFF

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

        if key == ord('t') and active_compliment:
            active_compliment = False
            thanked = True
            compliment_stop_flag.set()
            audio_manager.speak("No no, THANK YOU for being amazing!")
            threading.Timer(3.0, lambda: None).start()

        elif key == ord('q'):
            exit_program = True
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