import sys
import types
from unittest.mock import patch, MagicMock, call
import pytest
from .watcher import Watcher, process_error_rules, process_cluster
from queue import Queue
from queue import Queue

# pytest



@pytest.fixture
def dummy_config():
    cfg = MagicMock()
    cfg.config = {"clusters": [{"hostname": "h1"}, {"hostname": "h2"}]}
    cfg.emf_watcher_config = False
    cfg.scan_intervals = 2
    return cfg

@pytest.fixture
def dummy_cluster():
    cluster = MagicMock()
    cluster.name = "cluster1"
    cluster.emf_config = None
    cluster.handling_rules = []
    return cluster

def test_watcher_init_sets_metrics():
    watcher = Watcher()
    assert watcher.metrics["connect_clusters_total"] == 0
    assert watcher.metrics["connect_clusters_healthy"] == 0
    assert watcher.metrics["connect_clusters_unhealthy"] == 0
    assert watcher.keep_running is True
    assert hasattr(watcher, "exit_gracefully")

@patch("kafka_connect_watcher.watcher.ConnectCluster")
@patch("kafka_connect_watcher.watcher.init_emf_config")
@patch("kafka_connect_watcher.watcher.LOG")
@patch("kafka_connect_watcher.watcher.NUM_THREADS", 1)
def test_watcher_run_main_loop(mock_log, mock_init_emf, mock_connect_cluster, dummy_config, monkeypatch):
    # Setup dummy cluster
    dummy_cluster = MagicMock()
    dummy_cluster.name = "c1"
    dummy_cluster.emf_config = None
    dummy_cluster.handling_rules = []
    mock_connect_cluster.side_effect = lambda cluster, config: dummy_cluster

    watcher = Watcher()
    # Patch threading.Thread to run target immediately
    def fake_thread(target, daemon, args):
        class DummyThread:
            def start(self):
                # Put a dummy cluster and then break
                args[0].put([watcher, dummy_config, dummy_cluster], False)
                args[0].put([watcher, dummy_config, None], False)
                target(args[0])
            def join(self): pass
        return DummyThread()
    monkeypatch.setattr("threading.Thread", fake_thread)
    monkeypatch.setattr("kafka_connect_watcher.watcher.process_cluster", lambda q: None)
    # Patch sleep to avoid delay
    monkeypatch.setattr("kafka_connect_watcher.watcher.sleep", lambda x: None)
    # Patch handle_watcher_emf to avoid side effects
    monkeypatch.setattr("kafka_connect_watcher.watcher.handle_watcher_emf", lambda config, watcher: None)
    # Patch Queue.join to return immediately
    watcher.connect_clusters_processing_queue.join = lambda: None

    # Only run one loop
    def stop_after_first(*a, **kw):
        watcher.keep_running = False
    monkeypatch.setattr(watcher, "metrics", watcher.metrics)
    monkeypatch.setattr(watcher, "keep_running", True)
    monkeypatch.setattr("kafka_connect_watcher.watcher.dt", MagicMock(now=lambda: MagicMock(total_seconds=lambda: 0)))
    watcher.keep_running = True
    watcher.run(dummy_config)
    assert watcher.metrics["connect_clusters_total"] == 2

def test_exit_gracefully_sets_flag_and_exits(monkeypatch):
    watcher = Watcher()
    monkeypatch.setattr("builtins.exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    with pytest.raises(SystemExit):
        watcher.exit_gracefully(1, "signal")
    assert watcher.keep_running is False

def test_process_error_rules_success(monkeypatch):
    rule = MagicMock()
    cluster = MagicMock()
    cluster.emf_config = None
    watcher = MagicMock()
    watcher.metrics = {
        "connect_clusters_healthy": 0,
        "connect_clusters_unhealthy": 0,
    }
    monkeypatch.setattr("kafka_connect_watcher.watcher.publish_clusters_emf", lambda c: None)
    process_error_rules(rule, cluster, watcher)
    assert watcher.metrics["connect_clusters_healthy"] == 1
    assert watcher.metrics["connect_clusters_unhealthy"] == 0
    rule.execute.assert_called_once_with(cluster)

def test_process_error_rules_execute_exception(monkeypatch):
    class FailingRule:
        def execute(self, cluster):
            raise Exception("fail")
    rule = FailingRule()
    cluster = MagicMock()
    cluster.emf_config = None
    watcher = MagicMock()
    watcher.metrics = {
        "connect_clusters_healthy": 0,
        "connect_clusters_unhealthy": 0,
    }
    monkeypatch.setattr("kafka_connect_watcher.watcher.LOG", MagicMock())
    monkeypatch.setattr("kafka_connect_watcher.watcher.publish_clusters_emf", lambda c: None)
    process_error_rules(rule, cluster, watcher)
    assert watcher.metrics["connect_clusters_healthy"] == 0
    assert watcher.metrics["connect_clusters_unhealthy"] == 1

def test_process_error_rules_emf_exception(monkeypatch):
    rule = MagicMock()
    cluster = MagicMock()
    cluster.emf_config = True
    watcher = MagicMock()
    watcher.metrics = {
        "connect_clusters_healthy": 0,
        "connect_clusters_unhealthy": 0,
    }
    monkeypatch.setattr("kafka_connect_watcher.watcher.publish_clusters_emf", lambda c: (_ for _ in ()).throw(Exception("emf fail")))
    monkeypatch.setattr("kafka_connect_watcher.watcher.LOG", MagicMock())
    process_error_rules(rule, cluster, watcher)
    assert watcher.metrics["connect_clusters_healthy"] == 1

def test_process_cluster_runs_rules(monkeypatch):
    rule = MagicMock()
    cluster = MagicMock()
    cluster.handling_rules = [rule]
    watcher = MagicMock()
    config = MagicMock()
    q = Queue()
    q.put([watcher, config, cluster], False)
    q.put([watcher, config, None], False)
    monkeypatch.setattr("kafka_connect_watcher.watcher.process_error_rules", lambda h, c, w: h.execute(c))
    process_cluster(q)
    rule.execute.assert_called_once_with(cluster)

def test_process_cluster_breaks_on_none(monkeypatch):
    watcher = MagicMock()
    config = MagicMock()
    q = Queue()
    q.put([watcher, config, None], False)
    # Should not raise or hang
    process_cluster(q)from unittest.mock import MagicMock, patch
import pytest
from kafka_connect_watcher.watcher import Watcher, process_error_rules, process_cluster
from queue import Queue
from queue import Queue

# pytest



class DummyHandlingRule:
    def __init__(self):
        self.executed = False
    def execute(self, cluster):
        self.executed = True

class DummyCluster:
    def __init__(self, name="dummy", emf_config=False):
        self.name = name
        self.emf_config = emf_config
        self.handling_rules = []
    def __str__(self):
        return self.name

class DummyWatcher:
    def __init__(self):
        self.metrics = {
            "connect_clusters_total": 0,
            "connect_clusters_healthy": 0,
            "connect_clusters_unhealthy": 0,
        }

def test_process_error_rules_success(monkeypatch):
    rule = DummyHandlingRule()
    cluster = DummyCluster()
    watcher = DummyWatcher()
    monkeypatch.setattr("kafka_connect_watcher.watcher.publish_clusters_emf", lambda c: None)
    process_error_rules(rule, cluster, watcher)
    assert watcher.metrics["connect_clusters_healthy"] == 1
    assert watcher.metrics["connect_clusters_unhealthy"] == 0
    assert rule.executed

def test_process_error_rules_execute_exception(monkeypatch):
    class FailingRule(DummyHandlingRule):
        def execute(self, cluster):
            raise Exception("fail")
    rule = FailingRule()
    cluster = DummyCluster()
    watcher = DummyWatcher()
    monkeypatch.setattr("kafka_connect_watcher.watcher.LOG", MagicMock())
    monkeypatch.setattr("kafka_connect_watcher.watcher.publish_clusters_emf", lambda c: None)
    process_error_rules(rule, cluster, watcher)
    assert watcher.metrics["connect_clusters_healthy"] == 0
    assert watcher.metrics["connect_clusters_unhealthy"] == 1

def test_process_error_rules_emf_exception(monkeypatch):
    rule = DummyHandlingRule()
    cluster = DummyCluster(emf_config=True)
    watcher = DummyWatcher()
    monkeypatch.setattr("kafka_connect_watcher.watcher.publish_clusters_emf", lambda c: (_ for _ in ()).throw(Exception("emf fail")))
    monkeypatch.setattr("kafka_connect_watcher.watcher.LOG", MagicMock())
    process_error_rules(rule, cluster, watcher)
    assert watcher.metrics["connect_clusters_healthy"] == 1

def test_process_cluster_runs_rules(monkeypatch):
    rule = DummyHandlingRule()
    cluster = DummyCluster()
    cluster.handling_rules = [rule]
    watcher = DummyWatcher()
    config = MagicMock()
    q = Queue()
    q.put([watcher, config, cluster], False)
    monkeypatch.setattr("kafka_connect_watcher.watcher.process_error_rules", lambda h, c, w: h.execute(c))
    # Should not raise
    process_cluster(q)
    assert rule.executed

def test_process_cluster_breaks_on_none(monkeypatch):
    watcher = DummyWatcher()
    config = MagicMock()
    q = Queue()
    q.put([watcher, config, None], False)
    # Should not raise or hang
    process_cluster(q)

def test_exit_gracefully_sets_flag_and_exits(monkeypatch):
    watcher = Watcher()
    monkeypatch.setattr("builtins.exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    with pytest.raises(SystemExit):
        watcher.exit_gracefully(1, "signal")
    assert watcher.keep_running is False

def test_watcher_init_sets_metrics():
    watcher = Watcher()
    assert watcher.metrics["connect_clusters_total"] == 0
    assert watcher.metrics["connect_clusters_healthy"] == 0
    assert watcher.metrics["connect_clusters_unhealthy"] == 0

@patch("kafka_connect_watcher.watcher.ConnectCluster")
@patch("kafka_connect_watcher.watcher.init_emf_config")
@patch("kafka_connect_watcher.watcher.handle_watcher_emf")
@patch("kafka_connect_watcher.watcher.NUM_THREADS", 1)
def test_watcher_run_main_loop(mock_handle_emf, mock_init_emf, mock_connect_cluster, monkeypatch):
    # Setup dummy config and cluster
    class DummyConfig:
        config = {"clusters": [1]}
        emf_watcher_config = False
        scan_intervals = 1
    dummy_cluster = MagicMock()
    mock_connect_cluster.return_value = dummy_cluster
    watcher = Watcher()
    # Patch threading.Thread to run target immediately
    def fake_thread(target, daemon, args):
        class DummyThread:
            def start(self):
                # Put a dummy cluster and then break
                args[0].put([watcher, DummyConfig(), dummy_cluster], False)
                args[0].put([watcher, DummyConfig(), None], False)
                target(args[0])
            def join(self): pass
        return DummyThread()
    monkeypatch.setattr("threading.Thread", fake_thread)
    monkeypatch.setattr("kafka_connect_watcher.watcher.process_cluster", lambda q: None)
    watcher.run(DummyConfig())
    assert watcher.metrics["connect_clusters_total"] == 1