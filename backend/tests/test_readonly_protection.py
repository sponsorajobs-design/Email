import pytest
from backend.app.services.supabase_service import SupabaseService

def test_supabase_service_strictly_readonly():
    service = SupabaseService()
    # Confirm mutating methods do not exist
    assert not hasattr(service, "insert")
    assert not hasattr(service, "update")
    assert not hasattr(service, "delete")
    assert not hasattr(service, "upsert")
    assert not hasattr(service, "mutate")
    assert not hasattr(service, "truncate")

    # Read methods exist
    assert hasattr(service, "fetch_jobs")
    assert hasattr(service, "fetch_subscribers")
    assert hasattr(service, "test_connection")
