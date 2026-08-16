# ai_engine.py
import ollama
import json
import logging
from pydantic import BaseModel
from typing import List, Optional, Union

class SmartHomeAction(BaseModel):
    action: str
    target: str
    value: Optional[Union[int, str]] = None

class IntentSchema(BaseModel):
    actions: List[SmartHomeAction]

class AIEngine:
    def __init__(self):
        self.model = "qwen2.5:1.5b"
        self._ensure_model_available()
        self.system_prompt = """
        You are Yuri, an offline AI home assistant.
        Extract the intent from the user's input and map it to smart home actions.
        The input may contain more than one instruction (e.g. "turn on the
        kitchen light and lock the door") -- output one action object per
        instruction in the "actions" list.

        Valid targets are strictly: "living_room_light", "kitchen_light", "ac", "door_lock".

        Valid actions are strictly:
        - "turn_on" / "turn_off" -- targets: "living_room_light", "kitchen_light", "ac". value: null.
        - "lock" / "unlock" -- target: "door_lock" only. value: null.
        - "set_temperature" -- target: "ac" only. value: integer, the exact
          target temperature in Celsius (e.g. "AC 24 degrees" -> value 24).
          Setting a temperature always means the AC should be on.

        SHORTHAND RULE: users often drop the word "light" and/or "turn" and
        just name the room plus on/off (e.g. "kitchen off", "living room on",
        "kitchen on please"). Whenever a room name ("kitchen" / "living room")
        appears WITHOUT the word "AC"/"air conditioner"/"temperature" nearby,
        it always refers to that room's LIGHT ("kitchen_light" /
        "living_room_light") -- never the AC, even if no explicit target
        word like "light" is stated. Only use "ac" as the target when the
        input actually says "AC" / "air conditioner" / "temperature"/"degrees".

        Examples (input -> output action):
        "turn on the kitchen light" -> {"action": "turn_on", "target": "kitchen_light", "value": null}
        "kitchen off" -> {"action": "turn_off", "target": "kitchen_light", "value": null}
        "kitchen on" -> {"action": "turn_on", "target": "kitchen_light", "value": null}
        "living room off" -> {"action": "turn_off", "target": "living_room_light", "value": null}
        "living room on" -> {"action": "turn_on", "target": "living_room_light", "value": null}
        "turn on AC" -> {"action": "turn_on", "target": "ac", "value": null}
        "turn off AC" -> {"action": "turn_off", "target": "ac", "value": null}
        "AC 24 degrees" / "set the AC to 24 degrees" -> {"action": "set_temperature", "target": "ac", "value": 24}
        "unlock the door" -> {"action": "unlock", "target": "door_lock", "value": null}
        "lock the door" -> {"action": "lock", "target": "door_lock", "value": null}

        Output ONLY valid JSON matching this exact schema, and nothing else:
        {"actions": [{"action": "turn_on", "target": "kitchen_light", "value": null}]}
        """

    def _ensure_model_available(self):
        """Verify Ollama is running and that self.model is pulled locally.

        On a fresh device, Ollama may not be installed/running, or the
        model may simply never have been downloaded (models aren't part of
        the codebase -- 'ollama pull <model>' is a separate, per-machine
        step). If we don't check this up front, every single command
        silently fails inside parse_intent()'s try/except and the user just
        sees a generic 'didn't catch that' fallback -- which looks exactly
        like a wake-word/greeting-only bug, not a missing-model bug.
        """
        try:
            local = ollama.list()
            installed = {
                m.get("model") or m.get("name")
                for m in local.get("models", [])
            }
            if self.model not in installed:
                logging.info(f"Model '{self.model}' not found locally. Pulling it now (one-time download)...")
                ollama.pull(self.model)
                logging.info(f"Model '{self.model}' pulled successfully.")
        except Exception as e:
            raise RuntimeError(
                f"Could not reach Ollama or prepare model '{self.model}'.\n"
                f"On this device, make sure:\n"
                f"  1. Ollama is installed and running (try 'ollama serve').\n"
                f"  2. The model is pulled: run 'ollama pull {self.model}'.\n"
                f"Details: {e}"
            )

    def parse_intent(self, text: str) -> dict:
        """Sends text to Ollama and returns structured Python dictionary."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text}
                ],
                format="json",
                options={
                    "temperature": 0.0,
                    # Longer / multi-instruction commands produce a longer JSON
                    # reply (one object per action). The default prediction
                    # length can cut that off mid-object on compound commands,
                    # which then fails to parse -- give it more room.
                    "num_predict": 512,
                }
            )
            
            raw_content = response['message']['content']
            parsed_data = json.loads(raw_content)
            
            # Validate with Pydantic model to ensure safety
            validated_data = IntentSchema(**parsed_data)
            return validated_data.dict()
            
        except Exception as e:
            logging.error(f"AI Engine Error: {e}")
            return None