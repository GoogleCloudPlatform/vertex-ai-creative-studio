/**
* Copyright 2024 Google LLC
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

# moved{} blocks (Phase 2): the composite indexes are now rendered via for_each
# from local.firestore_indexes instead of being individually-named resources.
# These tell Terraform the addresses moved (config refactor), NOT destroy/create,
# so no index is dropped or recreated. Behavior-preserving.

moved {
  from = google_firestore_index.genmedia_library_mime_type_timestamp
  to   = google_firestore_index.genmedia["genmedia_library_mime_type_timestamp"]
}

moved {
  from = google_firestore_index.genmedia_chooser_media_type_timestamp
  to   = google_firestore_index.genmedia["genmedia_chooser_media_type_timestamp"]
}

moved {
  from = google_firestore_index.genmedia_user_email_timestamp
  to   = google_firestore_index.genmedia["genmedia_user_email_timestamp"]
}

moved {
  from = google_firestore_index.genmedia_user_email_mime_type_timestamp
  to   = google_firestore_index.genmedia["genmedia_user_email_mime_type_timestamp"]
}
