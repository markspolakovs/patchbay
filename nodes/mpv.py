from typing import Any, List, Mapping, Optional, Tuple
import subprocess
from ._node import Node, LinkPort
import jack


class MPV(Node):
    CONFIG_FIELDS = ("source",)
    source: str
    mpv: Optional[subprocess.Popen[Any]] = None
    ports: Optional[Tuple[jack.Port, jack.Port]] = None

    def __init__(self, id: str, config: Mapping[str, str]):
        Node.__init__(self, id, config)
        self.source = config["source"]
        self.OUTPUTS = [LinkPort(self, "0")]

    def update(self, config: Mapping[str, str]):
        super().update(config)
        self.source = config["source"]
        if self.mpv is not None:
            self.shutdown()
            self.start()

    def start(self):
        self.mpv = subprocess.Popen(
            [
                "mpv",
                "--ao=jack",
                f"--jack-name={self.id}",
                "--jack-connect=no",
                "--quiet",
                "--no-audio-display",
                self.source,
            ]
        )
        while True:
            ports = self._jack.get_ports(rf"{self.id}:out_(0|1)", is_audio=True)
            if len(ports) != 2:
                continue
            self.ports = (ports[0], ports[1])
            break

    def shutdown(self):
        if self.mpv is not None:
            self.mpv.terminate()
            self.ports = None

    def reconcile_links(self, links: List[Tuple[LinkPort, LinkPort]]):
        assert self.ports is not None
        for channel in range(2):
            existing_connections = self._jack.get_all_connections(self.ports[channel])
            existing_names = [port.name for port in existing_connections]
            new_conn_names = [
                link[1].node.get_input_ports(link[1])[channel] for link in links
            ]

            # out with the old
            for old in existing_connections:
                if old.name not in new_conn_names:
                    self._jack.disconnect(self.ports[channel], old)
            # and in with the new
            for new in new_conn_names:
                if new not in existing_names:
                    self._jack.connect(self.ports[channel], new)
