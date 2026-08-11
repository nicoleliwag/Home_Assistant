# main.py
# Project: AI-Powered Home Virtual Assistant

import tkinter as tk
import threading
import logging
import json
import re
from voice_pipeline import VoicePipeline
from ai_engine import AIEngine
from home_simulator import HomeSimulatorGUI

# Configure execution logging
logging.basicConfig(
    filename='assistant_execution.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

GREETING_WORDS = ("hi", "hello", "hey", "yo", "sup", "greetings",
                   "good morning", "good afternoon", "good evening")
GREETING_REPLY = "Hello! I'm Yuri, your home assistant. How can I help?"


def is_greeting(user_text):
    """True if the utterance is just a greeting (with or without the wake word),
    not a smart-home command. Kept short and keyword-only so it doesn't
    misfire on real commands like 'hey turn on the kitchen light'."""
    cleaned = re.sub(r'[^a-z0-9\s]', '', user_text.lower()).strip()
    words = [w for w in cleaned.split() if w != "yuri"]
    remainder = " ".join(words)

    if remainder == "":
        return True  # they just said "Yuri" / "Hey Yuri" with nothing else

    for pattern in GREETING_WORDS:
        if remainder == pattern or remainder.startswith(pattern + " "):
            if len(words) <= 4:  # keep it short so "hey turn on the lights" isn't caught
                return True
    return False


# main.py fragment
def assistant_loop(gui, voice, ai):
    """Background thread for handling continuous wake-word voice interactions."""
    logging.info("System initialized. Yuri is listening for the wake word...")
    
    while True:
        try:
            gui.set_voice_state("listening")
            gui.update_status("Listening (Say 'Hey Yuri')...")
            user_text = voice.listen()
            
            if user_text:
                logging.info(f"User Transcribed: {user_text}")
                gui.update_status(f"Heard: {user_text}")

                # NOTE: the "yuri" wake-word gate has been removed -- every
                # transcribed utterance is now treated as a potential
                # command, whether or not it's addressed to Yuri by name.
                # This means background speech (TV, other conversations,
                # etc.) picked up by the mic can also trigger actions or
                # the fallback response; see the trade-off note below.

                if is_greeting(user_text):
                    # Respond immediately -- no need to hit the LLM for a greeting
                    gui.set_voice_state("speaking")
                    gui.update_status(GREETING_REPLY)
                    voice.speak(GREETING_REPLY)
                    logging.info("Greeting detected and answered.")
                    continue

                gui.set_voice_state("thinking")
                gui.update_status("Processing...")
                logging.info("Processing transcribed speech as a command (no wake word required).")

                # Process intent via local Qwen model
                intent_dict = ai.parse_intent(user_text)
                logging.info(f"Parsed Dict: {intent_dict}")

                if intent_dict and 'actions' in intent_dict and len(intent_dict['actions']) > 0:
                    gui.execute_actions(intent_dict)

                    response_msg = gui.describe_actions(intent_dict)
                    gui.set_voice_state("speaking")
                    gui.update_status(response_msg)
                    voice.speak(response_msg)
                    logging.info(f"Action executed and confirmed: {response_msg}")
                else:
                    fail_msg = "Sorry, I didn't catch a valid command. Could you try again?"
                    gui.set_voice_state("speaking")
                    voice.speak(fail_msg)
                    gui.update_status("Command not recognized.")
                    logging.info("No valid actions parsed; spoke fallback response.")
                        
        except Exception as e:
            logging.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    # Initialize components
    root = tk.Tk()
    gui = HomeSimulatorGUI(root)

    try:
        voice = VoicePipeline()
    except Exception as e:
        logging.error(f"Fatal: could not initialize VoicePipeline: {e}")
        gui.update_status(f"Mic/model init failed: {e}")
        root.mainloop()  # keep the window open so the error is visible, but don't start the loop
        raise SystemExit(1)

    ai = AIEngine()

    # Start the assistant loop in a background thread
    ai_thread = threading.Thread(target=assistant_loop, args=(gui, voice, ai), daemon=True)
    ai_thread.start()

    root.protocol("WM_DELETE_WINDOW", lambda: (gui.shutdown(), root.destroy()))

    # Start GUI event loop
    root.mainloop()