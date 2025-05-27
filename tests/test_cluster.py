import pytest
from unittest.mock import MagicMock, patch
from .cluster import ConnectCluster

# pytest



@pytest.fixture
def minimal_cluster_config():
    return {
        "hostname": "localhost",
        "name": "test-cluster",
        "port": 1234,
        "metrics": {},
    }

@pytest.fixture
def watcher_config():
    return MagicMock()

@patch("kafka_connect_watcher.cluster.Api")
@patch("kafka_connect_watcher.cluster.Cluster")
@patch("kafka_connect_watcher.cluster.set_else_none", side_effect=lambda k, d, *a: d.get(k, a[0] if a else None))
@patch("kafka_connect_watcher.cluster.keyisset", side_effect=lambda k, d: k in d)
@patch("kafka_connect_watcher.cluster.EvaluationRule")
@patch("kafka_connect_watcher.cluster.EmfConfig")
def test_connect_cluster_init_basic(
    mock_emfconfig,
    mock_evalrule,
    mock_keyisset,
    mock_set_else_none,
    mock_cluster,
    mock_api,
    minimal_cluster_config,
    watcher_config,
):
    cluster = ConnectCluster(minimal_cluster_config, watcher_config)
    assert cluster.hostname == "localhost"
    assert cluster.name == "test-cluster"
    assert cluster.port == 1234
    assert isinstance(cluster.api, mock_api)
    assert isinstance(cluster.cluster, mock_cluster)
    assert isinstance(cluster.handling_rules, list)
    assert isinstance(cluster.metrics, dict)
    assert cluster.metrics["connectors"] == {}

def test_connect_cluster_typeerror(watcher_config):
    with pytest.raises(TypeError):
        ConnectCluster("notadict", watcher_config)

@patch("kafka_connect_watcher.cluster.Api")
@patch("kafka_connect_watcher.cluster.Cluster")
@patch("kafka_connect_watcher.cluster.set_else_none", side_effect=lambda k, d, *a: d.get(k, a[0] if a else None))
@patch("kafka_connect_watcher.cluster.keyisset", side_effect=lambda k, d: k in d)
@patch("kafka_connect_watcher.cluster.EvaluationRule")
@patch("kafka_connect_watcher.cluster.EmfConfig")
def test_connect_cluster_name_fallback(
    mock_emfconfig,
    mock_evalrule,
    mock_keyisset,
    mock_set_else_none,
    mock_cluster,
    mock_api,
    watcher_config,
):
    config = {
        "hostname": "hosty",
        "port": 5555,
        "metrics": {},
    }
    cluster = ConnectCluster(config, watcher_config)
    assert cluster.name == "hosty_8083" or cluster.name == "hosty_5555"

@patch("kafka_connect_watcher.cluster.Api")
@patch("kafka_connect_watcher.cluster.Cluster")
@patch("kafka_connect_watcher.cluster.set_else_none", side_effect=lambda k, d, *a: d.get(k, a[0] if a else None))
@patch("kafka_connect_watcher.cluster.keyisset", side_effect=lambda k, d: k in d)
@patch("kafka_connect_watcher.cluster.EvaluationRule")
@patch("kafka_connect_watcher.cluster.EmfConfig")
def test_connect_cluster_emf_high_resolution(
    mock_emfconfig,
    mock_evalrule,
    mock_keyisset,
    mock_set_else_none,
    mock_cluster,
    mock_api,
    minimal_cluster_config,
    watcher_config,
):
    cluster = ConnectCluster(minimal_cluster_config, watcher_config)
    # keyisset is patched to True for any key in dict, so this will be True if key is present
    cluster.emf_config = {"high_resolution_metrics": True}
    assert cluster.emf_high_resolution() is True