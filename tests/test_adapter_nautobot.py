"""Tests for the Nautobot target adapter conflict strategy logic.

These tests mock out the ORM so they can run without a live Nautobot instance.
"""

import pytest
from unittest.mock import MagicMock, patch

from nautobot_ssot_netcracker.diffsync.adapter_nautobot import NetCrackerNautobotAdapter
from nautobot_ssot_netcracker.diffsync.models import NetCrackerLocation, NetCrackerDevice


class TestConflictStrategies:
    """Test that sync_create / sync_update / sync_delete honour conflict strategies."""

    def _make_adapter(self):
        mock_job = MagicMock()
        mock_job.logger = MagicMock()
        adapter = NetCrackerNautobotAdapter.__new__(NetCrackerNautobotAdapter)
        adapter.job = mock_job
        adapter.sync = None
        return adapter

    def _make_location(self, name="NYC-DC1"):
        return NetCrackerLocation(name=name)

    # --- sync_create ---

    @patch("nautobot_ssot_netcracker.diffsync.adapter_nautobot.get_conflict_strategy", return_value="overwrite")
    @patch("nautobot_ssot.contrib.NautobotAdapter.sync_create", return_value=MagicMock())
    def test_create_overwrite_calls_super(self, mock_super_create, mock_strategy):
        adapter = self._make_adapter()
        obj = self._make_location()
        adapter.sync_create(obj)
        mock_super_create.assert_called_once_with(obj)

    @patch("nautobot_ssot_netcracker.diffsync.adapter_nautobot.get_conflict_strategy", return_value="flag")
    def test_create_flag_returns_none(self, mock_strategy):
        adapter = self._make_adapter()
        obj = self._make_location()
        result = adapter.sync_create(obj)
        assert result is None

    @patch("nautobot_ssot_netcracker.diffsync.adapter_nautobot.get_conflict_strategy", return_value="skip")
    @patch("nautobot_ssot.contrib.NautobotAdapter.sync_create", return_value=MagicMock())
    def test_create_skip_calls_super(self, mock_super_create, mock_strategy):
        """'skip' applies to updates only, not creates."""
        adapter = self._make_adapter()
        obj = self._make_location()
        adapter.sync_create(obj)
        mock_super_create.assert_called_once_with(obj)

    # --- sync_update ---

    @patch("nautobot_ssot_netcracker.diffsync.adapter_nautobot.get_conflict_strategy", return_value="overwrite")
    @patch("nautobot_ssot.contrib.NautobotAdapter.sync_update", return_value=MagicMock())
    def test_update_overwrite_calls_super(self, mock_super_update, mock_strategy):
        adapter = self._make_adapter()
        obj = self._make_location()
        adapter.sync_update(obj)
        mock_super_update.assert_called_once_with(obj)

    @patch("nautobot_ssot_netcracker.diffsync.adapter_nautobot.get_conflict_strategy", return_value="skip")
    def test_update_skip_returns_none(self, mock_strategy):
        adapter = self._make_adapter()
        obj = self._make_location()
        result = adapter.sync_update(obj)
        assert result is None

    @patch("nautobot_ssot_netcracker.diffsync.adapter_nautobot.get_conflict_strategy", return_value="flag")
    def test_update_flag_returns_none(self, mock_strategy):
        adapter = self._make_adapter()
        obj = self._make_location()
        result = adapter.sync_update(obj)
        assert result is None

    # --- sync_delete ---

    def test_delete_always_blocked(self):
        """Deletions should always be blocked regardless of conflict strategy."""
        adapter = self._make_adapter()
        obj = self._make_location()
        result = adapter.sync_delete(obj)
        assert result is None
        # Verify a warning was logged
        adapter.job.logger.warning.assert_called_once()
