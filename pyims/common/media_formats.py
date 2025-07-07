from typing import Optional
import enum



class MediaType(enum.Enum):
    AUDIO = 'audio'


class MediaFormat(object):

    def __init__(self, name: str, media_type: MediaType, bitrate: int, sample_rate: int, sample_width: int, channels: int):
        """

        :param name:
        :param media_type:
        :param bitrate: bit rate in bits/s
        :param sample_rate: same rate in samples/s
        :param sample_width: sample width in bytes
        :param channels: channel count
        """
        self._name = name
        self._media_type = media_type
        self._bitrate = bitrate
        self._sample_rate = sample_rate
        self._sample_width = sample_width
        self._channels = channels

    @property
    def name(self) -> str:
        return self._name

    @property
    def media_type(self) -> MediaType:
        return self._media_type

    @property
    def bitrate(self) -> int:
        # bitrate = samplerate * samplewidth * 8
        return self._bitrate

    @property
    def sample_rate(self) -> int:
        # samplerate = bitrate / (samplewidth * 8)
        return self._sample_rate

    @property
    def sample_width(self) -> int:
        # samplewidth = samplerate / bitrate / 8
        return self._sample_width

    @property
    def channels(self) -> int:
        return self._channels


# todo: should be width of 1, but only works as 2. why?
PCMU = MediaFormat('PCMU', MediaType.AUDIO, 64000, 8000, 2, 1)
PCMA = MediaFormat('PCMA', MediaType.AUDIO, 64000, 8000, 2, 1)


"""
    # see https://datatracker.ietf.org/doc/html/rfc3551 tables 4 and 5
    PCMU = 0, 8000, 1
    GSM = 3, 8000, 1
    G723 = 4, 8000, 1
    DVI4_8000 = 5, 8000, 1
    DVI4_16000 = 6, 16000, 1
    LPC = 7, 8000, 1
    PCMA = 8, 8000, 1
    G722 = 9, 8000, 1
    L16_2 = 10, 44100, 2
    L16 = 11, 44100, 1
    QCELP = 12, 8000, 1
    CN = 13, 8000, 1
    OPUS = 107, 48000, 2
    MPA = 14, 90000, 0
    G728 = 15, 8000, 1
    DVI4_11025 = 16, 11025, 1
    DVI4_22050 = 17, 22050, 1
    G729 = 18, 8000, 1
    CELB = 25, 90000, 0
    JPEG = 26, 90000, 0
    NV = 28, 90000, 0
    H261 = 31, 90000, 0
    MPV = 32, 90000, 0
    MP2T = 33, 90000, 1
    H263 = 34, 90000, 0
    EVENT = 121, 8000, 0
"""