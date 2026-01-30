# Copyright 2025 Google LLC
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

"""Provides temporary handlers for the Shop The Look feature during refactoring."""

import concurrent.futures
import datetime
import time
from types import SimpleNamespace

import mesop as me
import requests

import models.shop_the_look_workflow as shop_the_look_workflow
from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import download_from_gcs
from common.workflows import WorkflowStepResult
from config.default import Default
from models.gemini import (
    describe_images_and_look,
    final_image_critic,
    select_best_image_with_description,
)
from models.shop_the_look_models import ProgressionImage, ProgressionImages
from models.veo import image_to_video
from models.vto import generate_vto_image
from common.utils import create_display_url
from state.shop_the_look_state import PageState
from state.state import AppState

config = Default()


def on_click_veo(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo generate request handler"""
    state = me.state(PageState)
    state.is_loading = True
    state.show_error_dialog = False
    state.error_message = ""
    state.result_video_gcs_uri = ""
    state.result_video_display_url = ""
    state.timing = ""
    state.current_status = f"Generating video with Veo {state.veo_model}"
    yield

    print(f"Lights, camera, action!:\n{state.veo_prompt_input}")

    aspect_ratio = (
        "16:9" if state.veo_model == "3.0" else state.aspect_ratio
    )  # @param ["16:9", "9:16"]
    # TODO seed
    seed = 120
    # TODO set default FALSE instead of requiring
    rewrite_prompt = False
    start_time = time.time()  # Record the starting time
    gcs_uri = ""
    current_error_message = ""

    try:
        veo_prompt = state.veo_prompt_input

        # Attach products descriptions to Veo prompt
        for item in state.catalog:
            if item.look_id == state.look:
                veo_prompt += f"\n {item.ai_description}"
        op = image_to_video(
            veo_prompt,
            state.result_image_gcs_uri,
            seed,
            aspect_ratio,
            state.veo_sample_count,
            f"gs://{config.VIDEO_BUCKET}",
            rewrite_prompt,
            state.video_length,
            state.veo_model,
        )

        # Check for explicit errors in response
        if op.get("done") and op.get("error"):
            current_error_message = op["error"].get("message", "Unknown API error")
            print(f"API Error Detected: {current_error_message}")
            # No GCS URI in this case
            gcs_uri = ""
        elif op.get("done") and op.get("response"):
            response_data = op["response"]
            print(f"Response: {response_data}")

            if response_data.get("raiMediaFilteredCount", 0) > 0 and response_data.get(
                "raiMediaFilteredReasons"
            ):
                # Extract the first reason provided
                filter_reason = response_data["raiMediaFilteredReasons"][0]
                current_error_message = f"Content Filtered: {filter_reason}"
                print(f"Filtering Detected: {current_error_message}")
                gcs_uri = ""  # No GCS URI if content was filtered

            else:
                # Extract GCS URI from different possible locations
                if (
                    "generatedSamples" in response_data
                    and response_data["generatedSamples"]
                ):
                    # print(f"Generated Samples: {response_data["generatedSamples"]}")
                    gcs_uri = response_data["generatedSamples"][0].get("video", {}).get("uri", "")
                elif "videos" in response_data and response_data["videos"]:
                    # print(f"Videos: {response_data["videos"]}")
                    gcs_uri = response_data["videos"][0].get("gcsUri", "")

                if gcs_uri:
                    file_name = gcs_uri.split("/")[-1]
                    print("Video generated - use the following to copy locally")
                    print(f"gcloud storage cp {gcs_uri} {file_name}")
                    state.result_video_gcs_uri = gcs_uri
                    state.result_video_display_url = create_display_url(gcs_uri)
                else:
                    # Success reported, but no video URI found - treat as an error/unexpected state
                    current_error_message = "API reported success but no video URI was found in the response."
                    print(f"Error: {current_error_message}")
                    state.result_video_gcs_uri = ""  # Ensure no video is shown
        else:
            # Handle cases where 'done' is false or response structure is unexpected
            current_error_message = "Unexpected API response structure or operation not done."
            print(f"Error: {current_error_message}")
            state.result_video = ""

    # Catch specific exceptions you anticipate
    except ValueError as err:
        print(f"ValueError caught: {err}")
        current_error_message = f"Input Error: {err}"
    except requests.exceptions.HTTPError as err:
        print(f"HTTPError caught: {err}")
        current_error_message = f"Network/API Error: {err}"
    # Catch any other unexpected exceptions
    except Exception as err:
        print(f"Generic Exception caught: {type(err).__name__}: {err}")
        current_error_message = f"An unexpected error occurred: {err}"

    finally:
        end_time = time.time()  # Record the ending time
        execution_time = end_time - start_time  # Calculate the elapsed time
        print(f"Execution time: {execution_time} seconds")  # Print the execution time
        state.timing = f"Generation time: {round(execution_time)} seconds"
        app_state = me.state(AppState)

        #  If an error occurred, update the state to show the dialog
        if current_error_message:
            state.error_message = current_error_message
            state.show_error_dialog = True
            # Ensure no result video is displayed on error
            state.result_video_gcs_uri = ""
            state.result_video_display_url = ""
            yield

        try:
            item_to_log = MediaItem(
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=state.veo_prompt_input,
                original_prompt=state.veo_prompt_input,
                model=state.veo_model,
                mime_type="video/mp4",
                aspect=aspect_ratio,
                duration=float(execution_time),
                reference_image=state.reference_image_gcs_model,
                last_reference_image=None,
                # negative_prompt=request.negative_prompt,
                # enhanced_prompt_used=request.enhance_prompt,
                comment="veo default generation",
                gcsuri=gcs_uri,
                generation_time=execution_time,
            )
            add_media_item_to_firestore(item_to_log)

        except Exception as meta_err:
            # Handle potential errors during metadata storage itself
            print(f"CRITICAL: Failed to store metadata: {meta_err}")
            # Optionally, display another error or log this critical failure
            if not state.show_error_dialog:  # Avoid overwriting primary error
                state.error_message = f"Failed to store video metadata: {meta_err}"
                state.show_error_dialog = True

    state.is_loading = False
    state.current_status = ""
    yield
    print("Cut! That's a wrap!")


def on_click_vto_look(e: me.ClickEvent):  # pylint: disable=unused-argument
    """VTO generate request handler"""
    vto_start_time = time.time()
    state = me.state(PageState)
    state.tryon_started = True
    state.is_loading = True
    state.show_error_dialog = False  # Reset error state before starting
    state.error_message = ""
    state.timing = ""  # Clear previous timing
    yield

    look_articles = shop_the_look_workflow.get_selected_look()
    articles_for_vto = []

    if e.key == "primary":
        state.retry_counter = 0
    elif e.key == "retry":
        print(f"attempting retry {state.retry_counter}")
        if state.retry_counter >= int(state.max_retry):
            return

        state.retry_counter += 1

    if e.key == "retry":
        look_articles.reverse()

        failed_articles = list(
            filter(
                lambda critic_record: not critic_record.accurate,
                state.final_critic.image_accuracy,
            )
        )

        failed_article_paths = [
            f.article_image_path.split("/")[-1] for f in failed_articles
        ]

        for row in look_articles:
            if row.item_id.split("/")[-1] in failed_article_paths:
                articles_for_vto.append(row)
    else:
        articles_for_vto = look_articles

    images_to_process = shop_the_look_workflow.get_model_records(
        state.selected_model.model_id
    )

    status_prefix = {
        "alternate": "Alt View: ",
        "retry": f"Critic Retry {state.retry_counter}: ",
    }.get(e.key, "Primary View: ")

    for r in images_to_process:
        if (
            (e.key == "primary" and not r.primary_view)
            or (e.key == "alternate" and r.primary_view)
            or (e.key == "retry" and not r.primary_view)
        ):
            continue

        if e.key != "retry":
            state.reference_image_gcs_model = r.model_image
            state.current_status = "Generating catalog descriptions"
            yield
            step_start_time = time.time()
            yield WorkflowStepResult(
                step_name="describe_product",
                status="processing",
                message="Catalog Enrichment: Generating catalog description",
                duration_seconds=0,
                data={},
            )

        articles = [row.clothing_image for row in look_articles]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            if e.key != "retry":
                desc_future = executor.submit(describe_images_and_look, look_articles)

            article_image_bytes_list = list(executor.map(download_from_gcs, articles))

            if e.key != "retry":
                try:
                    result = desc_future.result()
                    state.look_description = result.look_description
                    for item in state.articles:
                        for article in result.articles:
                            if (
                                item.item_id.split("/")[-1]
                                == article.article_image_path.split("/")[-1]
                            ):
                                item.ai_description = article.article_description
                    yield
                except Exception as exc:
                    print(f"generated an exception: {exc}")

                step_duration = time.time() - step_start_time
                yield WorkflowStepResult(
                    step_name="describe_product",
                    status="complete",
                    message="Look and article description generated",
                    duration_seconds=step_duration,
                    data={},
                )

            for i, row in enumerate(articles_for_vto):
                state.current_status = f"{status_prefix}Trying on {row.article_type}..."
                yield

                potential_images = generate_vto_image(
                    person_gcs_uri=state.reference_image_gcs_model,
                    product_gcs_uri=row.clothing_image,
                    sample_count=int(state.vto_sample_count),
                )

                temp_progressions = [
                    ProgressionImage(image_path=p, best_image=False, reasoning="")
                    for p in potential_images
                ]

                reference_image_bytes_list = list(
                    executor.map(download_from_gcs, potential_images)
                )

                state.current_status = f"{status_prefix}Selecting best image of {row.article_type}..."
                yield

                byte_lookup = article_image_bytes_list[
                    articles.index(row.clothing_image)
                ]

                best_match = select_best_image_with_description(
                    [byte_lookup],
                    reference_image_bytes_list,
                    potential_images,
                    f"a {row.article_type}",
                    f"the {row.article_type}",
                )

                last_best_image = None
                for p in temp_progressions:
                    for bm in best_match.image_accuracy:
                        if bm.article_image_path == p.image_path:
                            p.best_image = bm.best_image
                            p.reasoning = bm.reasoning
                            p.accurate = bm.accurate
                            if bm.best_image:
                                last_best_image = p.image_path

                if last_best_image is None and potential_images:
                    # Fallback: if no 'best' image was flagged, use the last one generated.
                    last_best_image = potential_images[-1]

                progressions = ProgressionImages(progression_images=temp_progressions)

                if e.key == "retry":
                    state.retry_progression_images.append(progressions)
                elif r.primary_view:
                    state.progression_images.append(progressions)
                else:
                    state.alternate_progression_images.append(progressions)

                if r.primary_view and (i + 1) == len(articles_for_vto):
                    state.result_image_gcs_uri = last_best_image
                    state.result_image_display_url = create_display_url(last_best_image)
                elif i == len(look_articles):
                    state.alternate_gcs_uris.append(last_best_image)
                    state.alternate_display_urls.append(create_display_url(last_best_image))

                state.reference_image_gcs_model = last_best_image
                yield

    if e.key == "primary" or e.key == "retry":
        with concurrent.futures.ThreadPoolExecutor() as executor:
            final_image_bytes_list = list(
                executor.map(download_from_gcs, [state.result_image_gcs_uri])
            )
            state.current_status = "Critic evaluation in progress..."
            yield
            final_critic = final_image_critic(
                article_image_bytes_list,
                articles,
                final_image_bytes_list,
            )
            state.final_critic = final_critic
            state.final_accuracy = final_critic.accurate
            state.current_status = ""
            yield

            if not state.final_critic.accurate and state.retry_counter < int(
                state.max_retry
            ):
                new_event = SimpleNamespace(key="retry")
                yield from on_click_vto_look(new_event)
            elif state.generate_video:
                yield from on_click_veo(e)

    state.is_loading = False
    yield
