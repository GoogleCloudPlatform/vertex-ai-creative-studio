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

""" Generate Video using Veo with PredictionServiceClient """
import os
import time

from google.cloud import aiplatform_v1beta1

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
VEO = "veo-2.0-generate-exp"
api_regional_endpoint = f"{LOCATION}-aiplatform.googleapis.com"
veo_model = f"projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/{VEO}"
OUTPUT_GCS = os.getenv("OUTPUT_GCS") # gs://etc

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
    client = aiplatform_v1beta1.PredictionServiceClient(client_options=client_options)

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



def fetch_operation(lro_name):
    """ Long Running Operation fetch """
    client_options = {"api_endpoint": api_regional_endpoint}
    client = aiplatform_v1beta1.PredictionServiceClient(client_options=client_options)

    
    request = {"operationName": lro_name}
    # The generation usually takes 2 minutes. Loop 30 times, around 5 minutes.
    for i in range(30):
        resp = client.get_operation(request)
        if "done" in resp and resp["done"]:
            return resp
        time.sleep(10)


def show_video(op):
    """ show video """
    print(op)
    if op["response"]:
        for video in op["response"]["generatedSamples"]:
            gcs_uri = video["video"]["uri"]
            file_name = gcs_uri.split("/")[-1]
            print("Video generated - use the following to copy locally")
            print(f"gcloud storage cp {gcs_uri} {file_name}")


prompt = "A high-speed, low-angle tracking shot shows Megatron and Optimus Prime, in full metallic transformer mode, snowboarding down a snowy mountain, both intensely focused. Megatron unleashes a powerful ollie, kicking up a spray of snow, while Optimus counters with a smooth 180, his metallic limbs adjusting with surprising fluidity. The sunlight glints off their metallic surfaces as they carve through the fresh powder, the mountain backdrop a mix of dark green and white. They are engaged in a fierce battle of skill, each trying to outdo the other with gravity defying tricks and speed.  A cinematic wide shot captures Optimus Prime and Megatron, rendered as highly detailed metallic transformers, snowboarding down a steep slope, with dramatic backlighting illuminating them. The scene is awash in cool blues and whites. Megatron launches into an aerial flip, his body contorting mid-air, while Optimus Prime executes a precise 180, carving a perfect arc into the snow. The camera tracks their descent, their every move a demonstration of power and skill, the snow spraying beneath their boards as they engage in a fierce and competitive battle.  A dynamic POV shot from the perspective of a snowboarder on a mountain shows two towering transformers, Optimus Prime and Megatron, snowboarding with intense speed. Megatron initiates a sharp ollie, catching air, as Optimus Prime executes a fast 180 turn, both demonstrating their agility. The background features snowy peaks and blue skies, with blurred snow banks rushing by. The camera shakes with the speed of their descent, highlighting the ferocity and the pure athletic skill being displayed by the transformers as they race downhill.  A medium shot captures Optimus Prime and Megatron, depicted as full metallic transformers, locked in a thrilling snowboarding duel on a bright, sunny day on a snow-covered hill. The background is a vast expanse of white snow. Megatron executes a series of rapid turns, spraying snow, while Optimus Prime counters with a series of ollies, maintaining speed. Their metallic forms are captured in sharp detail, the scene filled with a sense of speed and intensity, their rivalry on full display as they push each other to the limits." 
aspect_ratio = "16:9"  # @param ["16:9", "9:16"]
output_gcs = OUTPUT_GCS
rewrite_prompt = False 
seed = 120
sample_count = 1


# PredictionServiceClient
op = t2v(prompt, seed, aspect_ratio, sample_count, output_gcs, rewrite_prompt)
show_video(op)
