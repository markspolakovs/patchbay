from typing import Any, Callable, List, Mapping, Optional, Tuple, TypeVar, Union
import subprocess
from ._node import Node, LinkPort
import jack
import time

T = TypeVar('T')
def flatten(src: List[Union[T, List[T]]]) -> List[T]:
    return [item for sublist in src for item in sublist]


class MPV(Node):
    PROP_FIELDS = ("source",)
    source: str
    mpv: Optional[subprocess.Popen[Any]] = None
    ports: Optional[Tuple[jack.Port, jack.Port]] = None

    def __init__(self, id: str, props: Mapping[str, str]):
        Node.__init__(self, id, props)
        self.source = props["source"]
        self.OUTPUTS = [LinkPort(self, "0")]

    def update(self, props: Mapping[str, str]):
        super().update(props)
        self.source = props["source"]
        if self.mpv is not None:
            self.shutdown()
            self.start()
            time.sleep(0.1)
            self._ctx.reconcile_node(self)

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
            while True:
                try:
                    ports = self._jack.get_ports(rf"{self.id}:out_(0|1)", is_audio=True)
                    if len(ports) < 2:
                        break
                except jack.JackError:
                    continue
            self.ports = None

    def reconcile_links(self, links: List[Tuple[LinkPort, LinkPort]]):
        assert self.ports is not None
        for channel in range(2):
            print(f"MPV reconciling channel {channel}")
            existing_connections = self._jack.get_all_connections(self.ports[channel])
            existing_names = [port.name for port in existing_connections]
            for pair in links:
                link = pair[1]
                print(f"getting input ports for {link.node}")
                new_conn_names = [x[channel] for x in link.node.get_input_ports(link)]
                print("; got", new_conn_names)
        
                # out with the old
                for old in existing_connections:
                    if old.name not in new_conn_names:
                        print(f"destroying {old.name}")
                        self._jack.disconnect(self.ports[channel], old)
                
                # and in with the new
                for new_conn in new_conn_names:
                    if new_conn not in existing_names:
                        print(f"creating {new_conn}")
                        self._jack.connect(self.ports[channel], new_conn)
        print("MPV: reconcile done")
