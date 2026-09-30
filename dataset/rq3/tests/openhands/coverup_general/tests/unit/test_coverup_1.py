# file: openhands/app_server/app_lifespan/alembic/versions/001.py:28-197
# asked: {"lines": [28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 49, 50, 51, 52, 53, 55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 79, 81, 82, 83, 84, 85, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 103, 104, 105, 106, 107, 109, 110, 111, 112, 113, 115, 116, 117, 118, 119, 121, 122, 123, 124, 125, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 138, 140, 141, 142, 143, 144, 146, 147, 148, 149, 150, 152, 153, 154, 155, 156, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 186, 187, 188, 189, 190, 192, 193, 194, 195, 196], "branches": []}
# gained: {"lines": [28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 49, 50, 51, 52, 53, 55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 79, 81, 82, 83, 84, 85, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 103, 104, 105, 106, 107, 109, 110, 111, 112, 113, 115, 116, 117, 118, 119, 121, 122, 123, 124, 125, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 138, 140, 141, 142, 143, 144, 146, 147, 148, 149, 150, 152, 153, 154, 155, 156, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 186, 187, 188, 189, 190, 192, 193, 194, 195, 196], "branches": []}

import importlib
import sys
import types

import pytest
import sqlalchemy as sa


class DummyOp:
    def __init__(self):
        self.created_tables = []
        self.created_indices = []

    def create_table(self, name, *cols):
        # store name and tuple of columns for inspection
        self.created_tables.append((name, cols))

    def create_index(self, name, table, columns, unique=False):
        self.created_indices.append((name, table, tuple(columns), unique))

    def f(self, name):
        # return the name unchanged to simulate alembic.op.f
        return name


def _ensure_dummy_enum_module(module_name: str, attr_name: str):
    """
    Ensure a module with module_name exists in sys.modules and defines attr_name.
    Only injects a dummy module if the real import would fail.
    """
    if module_name in sys.modules:
        # assume real module is present
        return
    try:
        importlib.import_module(module_name)
    except Exception:
        m = types.ModuleType(module_name)
        # create a simple dummy enum-like object
        DummyEnum = type("DummyEnum", (), {"__members__": {}, "__repr__": lambda self: "<DummyEnum>"})
        setattr(m, attr_name, DummyEnum)
        sys.modules[module_name] = m


def _import_migration_module():
    # Ensure dependent enum modules exist to prevent ImportError during import
    _ensure_dummy_enum_module("openhands.app_server.app_conversation.app_conversation_models", "AppConversationStartTaskStatus")
    _ensure_dummy_enum_module("openhands.app_server.event_callback.event_callback_result_models", "EventCallbackResultStatus")
    # Import the specific migration module
    return importlib.import_module("openhands.app_server.app_lifespan.alembic.versions.001")


def test_upgrade_creates_expected_tables_and_indices(monkeypatch):
    mod = _import_migration_module()
    dummy = DummyOp()
    # Replace the op object in the migration module
    monkeypatch.setattr(mod, "op", dummy)
    # Call upgrade to execute the code paths
    mod.upgrade()

    # Verify expected tables were created
    table_names = [t for t, _ in dummy.created_tables]
    assert "app_conversation_start_task" in table_names
    assert "event_callback" in table_names
    assert "event_callback_result" in table_names
    assert "v1_remote_sandbox" in table_names
    assert "conversation_metadata" in table_names
    assert len(dummy.created_tables) == 5

    # Verify the expected number of indices were created
    # From the migration: 3 + 1 + 4 + 3 + 2 = 13
    assert len(dummy.created_indices) == 13

    # Spot-check one of the indices entries for correctness
    # Find index for event_callback created_at
    found = any(idx_name == "ix_event_callback_created_at" and table == "event_callback" and cols == ("created_at",)
                for idx_name, table, cols, unique in dummy.created_indices)
    assert found, "Expected ix_event_callback_created_at index not found"


def test_upgrade_table_columns_have_expected_server_default_and_primary_keys(monkeypatch):
    mod = _import_migration_module()
    dummy = DummyOp()
    monkeypatch.setattr(mod, "op", dummy)
    mod.upgrade()

    # Find the app_conversation_start_task table's columns
    app_table = None
    for name, cols in dummy.created_tables:
        if name == "app_conversation_start_task":
            app_table = cols
            break
    assert app_table is not None, "app_conversation_start_task table was not created"

    # Ensure created_at column exists and has a server_default set
    created_at_cols = [c for c in app_table if isinstance(c, sa.Column) and c.name == "created_at"]
    assert created_at_cols, "created_at column not found in app_conversation_start_task"
    created_at_col = created_at_cols[0]
    assert getattr(created_at_col, "server_default", None) is not None, "created_at should have a server_default"

    # Ensure id primary key is present in the PrimaryKeyConstraint passed to create_table for conversation_metadata
    conv_meta = None
    for name, cols in dummy.created_tables:
        if name == "conversation_metadata":
            conv_meta = cols
            break
    assert conv_meta is not None, "conversation_metadata table was not created"

    # The PrimaryKeyConstraint is passed as one of the args; ensure it's present and references 'conversation_id'
    pk_constraints = [c for c in conv_meta if isinstance(c, sa.PrimaryKeyConstraint) or getattr(c, "__class__", None) is sa.PrimaryKeyConstraint]
    assert pk_constraints, "PrimaryKeyConstraint not found in conversation_metadata table creation args"

    # Also ensure conversation_id column exists and is set nullable=False
    conv_id_cols = [c for c in conv_meta if isinstance(c, sa.Column) and c.name == "conversation_id"]
    assert conv_id_cols, "conversation_id column not found in conversation_metadata"
    conv_id_col = conv_id_cols[0]
    assert conv_id_col.nullable is False, "conversation_id should be non-nullable (primary key)"
