from unittest.mock import patch

import pytest

from hyperliquid.info import Info


def test_metadata_failure_does_not_start_websocket():
    with patch("hyperliquid.info.WebsocketManager") as manager:
        with patch.object(Info, "spot_meta", side_effect=RuntimeError("metadata unavailable")):
            with pytest.raises(RuntimeError, match="metadata unavailable"):
                Info()
        manager.return_value.start.assert_not_called()


def test_websocket_starts_after_successful_initialization():
    with patch("hyperliquid.info.WebsocketManager") as manager:
        info = Info(meta={"universe": []}, spot_meta={"universe": [], "tokens": []})
        assert info.ws_manager is manager.return_value
        manager.return_value.start.assert_called_once_with()
