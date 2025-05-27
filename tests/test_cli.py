import sys
from unittest.mock import patch, MagicMock
import pytest
from .cli import start_watcher

# pytest




def test_start_watcher_runs(monkeypatch):
    # Simulate command line arguments
    test_args = ["prog", "-c", "test_config.yaml"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Patch Config and Watcher
    mock_config = MagicMock()
    mock_watcher = MagicMock()
    with patch("kafka_connect_watcher.cli.Config", return_value=mock_config) as config_patch, \
         patch("kafka_connect_watcher.cli.Watcher", return_value=mock_watcher) as watcher_patch:
        start_watcher()
        config_patch.assert_called_once()
        watcher_patch.assert_called_once()
        mock_watcher.run.assert_called_once_with(mock_config)

def test_start_watcher_passes_abspath(monkeypatch):
    test_args = ["prog", "--config-file", "some/path/config.yaml"]
    monkeypatch.setattr(sys, "argv", test_args)
    with patch("kafka_connect_watcher.cli.path.abspath", side_effect=lambda x: f"/abs/{x}") as abspath_patch, \
         patch("kafka_connect_watcher.cli.Config") as config_patch, \
         patch("kafka_connect_watcher.cli.Watcher") as watcher_patch:
        watcher_instance = watcher_patch.return_value
        start_watcher()
        abspath_patch.assert_called_once_with("some/path/config.yaml")
        config_patch.assert_called_once_with("/abs/some/path/config.yaml")
        watcher_instance.run.assert_called_once()

def test_start_watcher_argparse_required(monkeypatch):
    # No config file argument should cause SystemExit
    test_args = ["prog"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit):
        start_watcher()