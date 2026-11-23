import socket

import pytest
from conftest import NetworkBlocked


def test_guard_blocks_outside_hosts():
    """Broken case: without the guard this connect would leave the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(NetworkBlocked):
        s.connect(("93.184.216.34", 80))
    s.close()
