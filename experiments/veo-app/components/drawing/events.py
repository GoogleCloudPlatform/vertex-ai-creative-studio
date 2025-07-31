"""
Events for the drawing component.
"""

import dataclasses

import mesop as me


@dataclasses.dataclass
class DoodleSaveEvent(me.WebEvent):
    """
    Event that's dispatched when the user saves a doodle.
    """

    value: str
