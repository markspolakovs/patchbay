from typing import Mapping, Optional
import subprocess, signal
from ._node import Node, LinkPort

class IcecastOut(Node):
    stream_url: str
    stream: Optional[subprocess.Popen[str]] = None
    
    CONFIG_FIELDS = ('stream_url',)

    def __init__(self, id: str, config: Mapping[str, str]):
        Node.__init__(self, id, config)
        self.stream_url = config['stream_url']
        self.INPUTS = [LinkPort(self, "0")]

    def update(self, config: Mapping[str, str]):
        super().update(config)
        self.stream_url = config['stream_url']
        if self.stream is not None:
            self.shutdown()
            self.start()

    def start(self):
        self.cmd = subprocess.Popen([
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-nostats",
            "-f",
            "jack",
            "-i",
            self.id,
            "-acodec",
            "libmp3lame",
            "-ab",
            "192k",
            "-f",
            "mp3",
            self.stream_url
        ])
        # startup check
        while True:
            ports = self._jack.get_ports(rf'{self.id}:input_(1|2)', is_audio=True)
            if len(ports) == 2:
                break
    
    def shutdown(self):
        if self.cmd is not None:
            self.cmd.send_signal(signal.SIGQUIT)
    
    def get_input_ports(self, pseudo: LinkPort):
        return (self.id + ':input_1', self.id + ':input_2')
