import logging
import json
from datetime import datetime
from typing import Dict

from ontology_dc8f06af066e4a7880a5938933236037.config import ConfigClass
from ontology_dc8f06af066e4a7880a5938933236037.input import InputClass
from ontology_dc8f06af066e4a7880a5938933236037.output import OutputClass
from openfabric_pysdk.context import AppModel, State
from core.stub import Stub
from llm_handler import query_local_llm

# In-memory session memory
session_memory = []
MEMORY_FILE = "memory.json"

# Configurations for the app
configurations: Dict[str, ConfigClass] = dict()

############################################################
# Helper: Save interaction to memory (RAM + disk)
############################################################
def save_interaction(prompt, expanded_prompt, image_url, model_url):
    entry = {
        "prompt": prompt,
        "expanded_prompt": expanded_prompt,
        "image_url": image_url,
        "model_url": model_url,
        "timestamp": datetime.now().isoformat()
    }
    session_memory.append(entry)
    try:
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logging.error(f"Failed to write to memory file: {e}")

############################################################
# Optional: Load memory from disk
############################################################
def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f]
    except FileNotFoundError:
        return []
    except Exception as e:
        logging.error(f"Failed to load memory file: {e}")
        return []

############################################################
# Config callback function
############################################################
def config(configuration: Dict[str, ConfigClass], state: State) -> None:
    for uid, conf in configuration.items():
        logging.info(f"Saving new config for user with id:'{uid}'")
        configurations[uid] = conf

############################################################
# Execution callback function
############################################################
def execute(model: AppModel) -> None:
    request: InputClass = model.request
    response: OutputClass = model.response

    user_config: ConfigClass = configurations.get('super-user', None)
    logging.info(f"Loaded configurations: {configurations}")

    if not user_config or len(user_config.app_ids) < 2:
        response.message = "Error: Missing required Openfabric app IDs in config."
        return

    original_prompt = request.prompt
    expanded_prompt = query_local_llm(original_prompt)

    # Use only the App IDs, not hostnames
    text_to_image_app_id = user_config.app_ids[0]
    image_to_3d_app_id = user_config.app_ids[1]
    stub = Stub([text_to_image_app_id, image_to_3d_app_id])

    # Step 2: Generate image from prompt using Openfabric Text-to-Image app
    try:
        image_output = stub.call(
            text_to_image_app_id,
            {'prompt': expanded_prompt},
            'super-user'
        )
    except Exception as e:
        response.message = f"Error: Exception during image generation: {e}"
        return

    image_url = image_output.get('image_url') or image_output.get('result')
    if not image_url:
        response.message = "Error: Failed to generate image from prompt."
        return

    # Step 3: Generate 3D model from image using Openfabric Image-to-3D app
    try:
        model_output = stub.call(
            image_to_3d_app_id,
            {'image_url': image_url},
            'super-user'
        )
    except Exception as e:
        response.message = f"Error: Exception during 3D model generation: {e}"
        return

    model_url = model_output.get('model_url') or model_output.get('result')
    if not model_url:
        response.message = "Error: Failed to generate 3D model from image."
        return

    save_interaction(original_prompt, expanded_prompt, image_url, model_url)

    response.message = (
        f"Prompt Expanded: {expanded_prompt}\n\n"
        f"🖼️ Image URL: {image_url}\n"
        f"🧊 3D Model URL: {model_url}"
    )

if __name__ == "__main__":
    # Simulate a test run for the pipeline
    from ontology_dc8f06af066e4a7880a5938933236037.input import InputClass
    from ontology_dc8f06af066e4a7880a5938933236037.output import OutputClass
    from openfabric_pysdk.context import AppModel

    # Use the correct App IDs from your config
    class DummyConfig:
        app_ids = [
            "f0997a01-d6d3-a5fe-53d8-561300318557",  # Text-to-Image
            "69543f29-4d41-4afc-7f29-3d51591f11eb"   # Image-to-3D
        ]
    configurations['super-user'] = DummyConfig()

    test_input = InputClass()
    test_input.prompt = "Make me a glowing dragon standing on a cliff at sunset."
    test_output = OutputClass()
    model = AppModel(request=test_input, response=test_output)

    execute(model)
    print("Pipeline output:\n", model.response.message)