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

        Examples (input -> output action):
        "turn on the kitchen light" -> {"action": "turn_on", "target": "kitchen_light", "value": null}
        "turn on AC" -> {"action": "turn_on", "target": "ac", "value": null}
        "turn off AC" -> {"action": "turn_off", "target": "ac", "value": null}
        "AC 24 degrees" / "set the AC to 24 degrees" -> {"action": "set_temperature", "target": "ac", "value": 24}
        "unlock the door" -> {"action": "unlock", "target": "door_lock", "value": null}
        "lock the door" -> {"action": "lock", "target": "door_lock", "value": null}

        Output ONLY valid JSON matching this exact schema, and nothing else:
        {"actions": [{"action": "turn_on", "target": "kitchen_light", "value": null}]}
        """

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