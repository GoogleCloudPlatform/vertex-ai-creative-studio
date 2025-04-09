# Copyright 2024 Google LLC
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
import mesop as me

from components.header import header
from components.page_scaffold import (
    page_scaffold,
    page_frame,
)
from common.metadata import get_elo_ratings


def leaderboard_page_content(app_state: me.state):
    """Another Mesop Page"""
    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Leaderboard", "leaderboard")

            df = get_elo_ratings(app_state.study)

            with me.box(
                style=me.Style(align_items="center", display="flex", justify_content="space-evenly")
            ):
                with me.box(style=me.Style(padding=me.Padding.all(10), width=500)):
                    me.table(
                        df,
                        #on_click=on_click,
                        header=me.TableHeader(sticky=True),
                        columns={
                            "NA": me.TableColumn(sticky=True),
                            "Index": me.TableColumn(sticky=True),
                        },
                    )
