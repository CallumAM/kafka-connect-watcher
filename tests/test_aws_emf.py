from unittest.mock import MagicMock, patch

import pytest

from kafka_connect_watcher.aws_emf import (
    handle_watcher_emf,
    init_emf_config,
    publish_cluster_metrics,
    publish_clusters_emf,
    publish_connector_metrics,
    publish_watcher_emf_metrics,
)
from kafka_connect_watcher.cluster import ConnectCluster
from kafka_connect_watcher.config import Config
from kafka_connect_watcher.watcher import Watcher


def test_init_emf_config():
    config = MagicMock()
    config.emf_service_name = "test_service"
    config.emf_service_type = "test_type"
    config.emf_log_group = "test_log_group"

    with patch(
        "kafka_connect_watcher.aws_emf.get_event_loop", side_effect=RuntimeError
    ), patch("kafka_connect_watcher.aws_emf.new_event_loop") as mock_new_loop, patch(
        "kafka_connect_watcher.aws_emf.set_event_loop"
    ) as mock_set_loop, patch(
        "kafka_connect_watcher.aws_emf.emf_config"
    ) as mock_emf_config:
        mock_loop = MagicMock()
        mock_new_loop.return_value = mock_loop

        init_emf_config(config)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        assert mock_emf_config.service_name == "test_service"
        assert mock_emf_config.service_type == "test_type"
        assert mock_emf_config.log_group_name == "test_log_group"


@patch("kafka_connect_watcher.aws_emf.LOG")
def test_publish_cluster_metrics(mock_log):
    cluster = MagicMock()
    cluster.name = "test_cluster"
    cluster.emf_config.emf_resolution = 60
    cluster.metrics = {"metric1": 100, "metric2": "invalid"}

    metrics = MagicMock()

    publish_cluster_metrics(cluster, metrics)

    metrics.reset_dimensions.assert_called_once_with(use_default=False)
    metrics.set_property.assert_called_once_with(
        "ConnectDetails", {"designation": "test_cluster"}
    )
    metrics.put_dimensions.assert_called_once()
    metrics.put_metric.assert_called_once_with("metric1", 100, None, 60)


@patch("kafka_connect_watcher.aws_emf.LOG")
def test_publish_connector_metrics(mock_log):
    cluster = MagicMock()
    cluster.name = "test_cluster"
    cluster.emf_config.emf_resolution = 60
    cluster.emf_config.namespace = "test_namespace"
    cluster.emf_config.dimensions = {"key": "value"}

    metrics = MagicMock()
    connector_name = "test_connector"
    connector_metrics = {"metric1": 100}

    publish_connector_metrics(cluster, connector_name, connector_metrics, metrics)

    metrics.set_namespace.assert_called_once_with("test_namespace")
    metrics.reset_dimensions.assert_called_once_with(use_default=False)
    metrics.set_property.assert_called_once_with(
        "ConnectDetails", {"designation": "test_cluster"}
    )
    metrics.put_dimensions.assert_called_once_with(
        {
            "key": "value",
            "ConnectorName": "test_connector",
            "ConnectCluster": "test_cluster",
        }
    )
    metrics.put_metric.assert_called_once_with("metric1", 100, None, 60)


@patch("kafka_connect_watcher.aws_emf.publish_cluster_metrics")
@patch("kafka_connect_watcher.aws_emf.publish_connector_metrics")
def test_publish_clusters_emf(mock_publish_connector, mock_publish_cluster):
    cluster = MagicMock()
    cluster.emf_config.enabled = True
    cluster.metrics = {"connectors": {"connector1": {"metric1": 100}}}

    with patch(
        "kafka_connect_watcher.aws_emf.get_event_loop", side_effect=RuntimeError
    ), patch("kafka_connect_watcher.aws_emf.new_event_loop") as mock_new_loop, patch(
        "kafka_connect_watcher.aws_emf.set_event_loop"
    ) as mock_set_loop:
        mock_loop = MagicMock()
        mock_new_loop.return_value = mock_loop

        publish_clusters_emf(cluster)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        mock_publish_cluster.assert_called_once_with(cluster)
        mock_publish_connector.assert_called_once_with(
            cluster, "connector1", {"metric1": 100}
        )


@patch("kafka_connect_watcher.aws_emf.LOG")
def test_publish_watcher_emf_metrics(mock_log):
    config = MagicMock()
    config.emf_watcher_config.emf_resolution = 60
    config.emf_watcher_config.namespace = "test_namespace"
    config.emf_watcher_config.dimensions = {"key": "value"}

    watcher = MagicMock()
    watcher.metrics = {"metric1": 100}

    metrics = MagicMock()

    publish_watcher_emf_metrics(config, watcher, metrics)

    metrics.set_namespace.assert_called_once_with("test_namespace")
    metrics.reset_dimensions.assert_called_once_with(use_default=False)
    metrics.put_dimensions.assert_called_once_with({"key": "value"})
    metrics.put_metric.assert_called_once_with("metric1", 100, None, 60)


@patch("kafka_connect_watcher.aws_emf.publish_watcher_emf_metrics")
def test_handle_watcher_emf(mock_publish_watcher):
    config = MagicMock()
    config.emf_watcher_config.enabled = True

    watcher = MagicMock()

    handle_watcher_emf(config, watcher)

    mock_publish_watcher.assert_called_once_with(config, watcher)
