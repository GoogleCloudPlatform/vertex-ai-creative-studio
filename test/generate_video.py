# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Generate Video using Veo """
import os
import time
from typing import Dict

import google.auth
import google.auth.transport.requests
import mediapy as media
import requests
from google.cloud import aiplatform_v1beta1 as aiplatform
from google.protobuf import json_format

# from google.protobuf.struct_pb2 import Value


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
#VEO = "veo-2.0-generate-exp"
VEO = "veo-2.0-generate-001"
api_regional_endpoint = f"{LOCATION}-aiplatform.googleapis.com"
veo_model = f"projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/{VEO}"

video_model = f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/{VEO}"
prediction_endpoint = f"{video_model}:predictLongRunning"
fetch_endpoint = f"{video_model}:fetchPredictOperation"



def compose_videogen_request(
    prompt,
    image_uri,
    gcs_uri,
    seed,
    aspect_ratio,
    sample_count,
    enable_prompt_rewriting,
):
    """ Create a JSON Request for Veo """
    instance = {"prompt": prompt}
    if image_uri:
        instance["image"] = {"gcsUri": image_uri, "mimeType": "png"}
    request = {
        "instances": [instance],
        "parameters": {
            "storageUri": gcs_uri,
            "sampleCount": sample_count,
            "seed": seed,
            "aspectRatio": aspect_ratio,
            "enablePromptRewriting": enable_prompt_rewriting,
        },
    }
    return request


def text_to_video(prompt, seed, aspect_ratio, sample_count, output_gcs, enable_pr):
    """ Text to Video """
    req = compose_videogen_request(
        prompt, None, output_gcs, seed, aspect_ratio, sample_count, enable_pr
    )
    resp = send_request_to_google_api(prediction_endpoint, req)
    print(resp)
    return fetch_operation(resp["name"])


def image_to_video(
    prompt, image_gcs, seed, aspect_ratio, sample_count, output_gcs, enable_pr
):
    """ Image to Video """
    req = compose_videogen_request(
        prompt, image_gcs, output_gcs, seed, aspect_ratio, sample_count, enable_pr
    )
    resp = send_request_to_google_api(prediction_endpoint, req)
    print(resp)
    return fetch_operation(resp["name"])


def t2v(prompt, seed, aspect_ratio, sample_count, output_gcs, enable_pr):
    """ Text to Video, using the AI Platform service Prediction client"""
    req = compose_videogen_request(
        prompt, None, output_gcs, seed, aspect_ratio, sample_count, enable_pr
    )
    resp = predict_veo_model( req)
    print(resp)
    return fetch_operation(resp["name"])


def predict_veo_model(
    data=None
):
    """ AI Platform Prediction Service Client """
    client_options = {"api_endpoint": api_regional_endpoint}
    client = aiplatform.PredictionServiceClient(client_options=client_options)

    print(api_regional_endpoint)
    #print(f"Instances: {data['instances']}")
    #print(f"Parameters: {data['parameters']}")
    print(veo_model)

    response = client.predict(
        endpoint=veo_model, 
        instances=data["instances"], 
        parameters=data["parameters"],
    )
    print("response")
    print(" deployed_model_id:", response.deployed_model_id)
    predictions = response.predictions
    for prediction in predictions:
        print(" prediction:", dict(prediction))

    return predictions.json()


def send_request_to_google_api(api_endpoint, data=None):
    """
    Sends an HTTP request to a Google API endpoint.

    Args:
        api_endpoint: The URL of the Google API endpoint.
        data: (Optional) Dictionary of data to send in the request body (for POST, PUT, etc.).

    Returns:
        The response from the Google API.
    """

    # Get access token calling API
    creds, project = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    access_token = creds.token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(api_endpoint, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def fetch_operation(lro_name):
    """ Long Running Operation fetch """
    request = {"operationName": lro_name}
    # The generation usually takes 2 minutes. Loop 30 times, around 5 minutes.
    for i in range(30):
        resp = send_request_to_google_api(fetch_endpoint, request)
        if "done" in resp and resp["done"]:
            return resp
        print(f"{i:4d} waiting ... {resp}")
        time.sleep(10)


def show_video(op):
    """ show video """
    print(op)
    gcs_uri = ""
    if op["response"]:
        if "generatedSamples" in op["response"] and op["response"]["generatedSamples"]:
            for video in op["response"]["generatedSamples"]:
                gcs_uri = video["video"]["uri"]
        elif "videos" in op["response"] and op["response"]["videos"]:
            #elif op["response"]["videos"]:
                # veo-2.0-generate-001
                videos = op["response"]["videos"]
                print(f"Videos: {len(videos)}")
                for video in videos:
                    print(f"> {video}")
                    gcs_uri = video["gcsUri"]
        else:
            print(f"something else has happened: {op['response']}")
        file_name = gcs_uri.split("/")[-1]
        print("Video generated - use the following to copy locally")
        print(f"gcloud storage cp {gcs_uri} {file_name}")

#prompt = "A high-speed, low-angle tracking shot shows Megatron and Optimus Prime, in full metallic transformer mode, snowboarding down a snowy mountain, both intensely focused. Megatron unleashes a powerful ollie, kicking up a spray of snow, while Optimus counters with a smooth 180, his metallic limbs adjusting with surprising fluidity. The sunlight glints off their metallic surfaces as they carve through the fresh powder, the mountain backdrop a mix of dark green and white. They are engaged in a fierce battle of skill, each trying to outdo the other with gravity defying tricks and speed.  A cinematic wide shot captures Optimus Prime and Megatron, rendered as highly detailed metallic transformers, snowboarding down a steep slope, with dramatic backlighting illuminating them. The scene is awash in cool blues and whites. Megatron launches into an aerial flip, his body contorting mid-air, while Optimus Prime executes a precise 180, carving a perfect arc into the snow. The camera tracks their descent, their every move a demonstration of power and skill, the snow spraying beneath their boards as they engage in a fierce and competitive battle.  A dynamic POV shot from the perspective of a snowboarder on a mountain shows two towering transformers, Optimus Prime and Megatron, snowboarding with intense speed. Megatron initiates a sharp ollie, catching air, as Optimus Prime executes a fast 180 turn, both demonstrating their agility. The background features snowy peaks and blue skies, with blurred snow banks rushing by. The camera shakes with the speed of their descent, highlighting the ferocity and the pure athletic skill being displayed by the transformers as they race downhill.  A medium shot captures Optimus Prime and Megatron, depicted as full metallic transformers, locked in a thrilling snowboarding duel on a bright, sunny day on a snow-covered hill. The background is a vast expanse of white snow. Megatron executes a series of rapid turns, spraying snow, while Optimus Prime counters with a series of ollies, maintaining speed. Their metallic forms are captured in sharp detail, the scene filled with a sense of speed and intensity, their rivalry on full display as they push each other to the limits." 
# prompt = """Introduction of the G-Wagon: A sleek, dark-colored G-Wagon is introduced. It's not parked idly. We see it confidently navigating the snowy streets, with its headlights cutting through the falling snow. Emphasize its powerful presence and capability. Close-ups on the tires gripping the snow, the robust frame, and the iconic G-Wagon design elements.

# We glimpse a sophisticated, well-dressed individual (male, 35-50) behind the wheel. They are focused, confident, and in control. Quick shots of them making a call on a high-end phone, checking market data on a tablet, or reviewing documents. Their expressions suggest they are managing complex, high-stakes situations.

# The G-Wagon isn't just a vehicle; it's an extension of the investor's lifestyle. The snowy conditions symbolize market volatility and uncertainty. The G-Wagon becomes a metaphor for stability, security, and the ability to navigate challenging circumstances.

# Scene 2: The G-Wagon effortlessly tackles the snowy streets, passing other vehicles struggling with the conditions. We see the investor's confidence grow as they navigate the challenges with ease.

# """

# Travel Motion
# prompt = """Imagine the sound of crashing waves as our camera focuses intently on a timeless travel companion: a vintage leather suitcase, lovingly scarred with memories. Each travel sticker adorning its weathered surface whispers tales of far-off lands and unforgettable adventures. Notice the intricate details – the scuffs, the worn edges, the vibrant colors that pop against the sandy canvas. The soft-focus background of the surf adds a gentle sense of motion, hinting at the endless possibilities that await. Let your imagination wander as you envision the journeys this suitcase has undertaken, carrying dreams and souvenirs across continents.

# As the camera slowly pans back, the world expands beyond the suitcase, revealing the breathtaking beauty of the beach. The rolling waves intensify, creating a mesmerizing dance of light and shadow. But the vintage suitcase remains our central focus, a tangible link to the past and a symbol of the enduring spirit of travel. Let this image ignite your wanderlust and inspire you to embark on your own unforgettable adventures. What stories will your luggage tell?
# """




# Stadium Allegient prompt

prompt = """Award-winning drone footage from above Allegiant Stadium during a Google-sponsored concert. The initial frame showcases the stage, now alive with activity. The band is in full swing, silhouettes against the backdrop of dazzling stage lights that shift from intense blues to vibrant greens, yellows and reds. Sound systems deliver booming basslines that shake the crowd. The camera smoothly pans up and back, revealing the stadium entirely filled with cheering attendees, caught up in the sonic wave. The drone glides through the stadium, capturing the full scale of the event, with laser beams crisscrossing the crowd. High-definition screens display the Google wordmark alongside the Google logo, and morph into a stylish Google Cloud logo – a vibrant cloud rendered in distinct Google colors, blue, green, yellow, and red, creating a visual spectacle, mirroring the frenetic energy on stage.

"""

prompt = """show the shoe getting chopped in half, the guillotine's steampunk gears moving, while the blade drops dramatically and slow, eventually splitting the shoe in half and falling to the table"""


aspect_ratio = "16:9"  # @param ["16:9", "9:16"]
output_gcs = (
    "gs://genai-blackbelt-fishfooding-ghchinoy/videos"  
)
rewrite_prompt = False
seed = 120
sample_count = 1

# Stadium image
source_gcs = (
    #"gs://ghchinoy-genai-sa-assets-flat/1741753524889/sample_2.png"
    #"gs://genai-blackbelt-fishfooding-ghchinoy/images/imagen_allegiant_003.png"
    "gs://genai-blackbelt-fishfooding-genmedia/shoe_chop.png"
)
# Travel image
# source_gcs = (
#     "gs://genai-blackbelt-fishfooding-ghchinoy/images/beach_travel_luggage.png"
# )


start_time = time.time()  # Record the starting time

# HTTP API
#op = text_to_video(prompt, seed, aspect_ratio, sample_count, output_gcs, rewrite_prompt)
#show_video(op)

# HTTP API
op = image_to_video(prompt, source_gcs, seed, aspect_ratio, sample_count, output_gcs, rewrite_prompt)
show_video(op)

# PredictionServiceClient
#op = t2v(prompt, seed, aspect_ratio, sample_count, output_gcs, rewrite_prompt)
#show_video(op)

end_time = time.time()  # Record the ending time
execution_time = end_time - start_time  # Calculate the elapsed time

print(f"Execution time: {execution_time} seconds")  # Print the execution time
