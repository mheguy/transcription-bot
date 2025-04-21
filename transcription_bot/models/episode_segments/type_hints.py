from typing import NewType

from transcription_bot.models.episode_segments.base import BaseSegment

RawSegments = NewType("RawSegments", list[BaseSegment])
TranscribedSegments = NewType("TranscribedSegments", list[BaseSegment])
GenericSegmentList = list[BaseSegment]
