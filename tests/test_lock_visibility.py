"""Test for visibility handling of lock entities."""
from unittest.mock import MagicMock

import unittest
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


from custom_components.fermax_duoxme.lock import async_setup_entry
from custom_components.fermax_duoxme.const import DOMAIN
from custom_components.fermax_duoxme.api.models import AccessDoor, DoorId

@pytest.fixture
def mock_coordinator(hass):
    """Mock coordinator."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = MagicMock()
    coordinator.data.devices = {}
    return coordinator

@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.async_on_unload = MagicMock()
    return entry

async def test_entity_availability_updates(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test entities become available/unavailable based on visibility."""
    
    # Setup mocks
    hass.data = {DOMAIN: {mock_config_entry.entry_id: {"coordinator": mock_coordinator}}}
    hass.async_create_task = MagicMock()
    async_add_entities = MagicMock()
    
    # 1. Initial Setup with a visible door
    door1 = AccessDoor(
        door_id=DoorId(1, 0, 1), title="Door 1", visible=True, door_type="ZERO"
    )
    mock_pairing = MagicMock()
    # Mock all_doors (used by lock.py)
    mock_pairing.all_doors = [door1]
    mock_pairing.tag = "My House"
    
    mock_device_data = MagicMock()
    mock_device_data.pairing = mock_pairing
    mock_coordinator.data.devices = {"dev1": mock_device_data}
    
    await async_setup_entry(hass, mock_config_entry, async_add_entities)
    
    # Get the entity
    assert async_add_entities.call_count == 1
    entity = async_add_entities.call_args[0][0][0]
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    
    # Verify initially available
    # CoordinatorEntity defaults to True, but let's check our logic didn't break it
    # We might need to ensure _attr_available is set or default is used
    # FermaxLock update logic sets it.
    
    # Trigger initial update explicitly just in case setup didn't call update logic fully on the instance
    entity._handle_coordinator_update()
    assert entity.available is True
    
    # 2. Update door to be INVISIBLE (Hidden)
    door1_hidden = AccessDoor(
        door_id=DoorId(1, 0, 1), title="Door 1", visible=False, door_type="ZERO"
    )
    mock_pairing.all_doors = [door1_hidden]
    
    # Mock entity registry
    mock_registry = MagicMock()
    mock_registry_entry = MagicMock()
    # Initial state: not disabled
    mock_registry_entry.disabled_by = None
    mock_registry.async_get.return_value = mock_registry_entry
    
    # Mock er.async_get
    with unittest.mock.patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_registry):
        # Trigger update on the entity
        entity._handle_coordinator_update()
        
        # Verify entity registry update called to DISABLE
        mock_registry.async_update_entity.assert_called_with(
            entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
        )
        
        # 3. Update door to be VISIBLE again
        door1_visible = AccessDoor(
            door_id=DoorId(1, 0, 1), title="Door 1", visible=True, door_type="ZERO"
        )
        mock_pairing.all_doors = [door1_visible]
        
        # Simulate registry now showing disabled
        mock_registry_entry.disabled_by = er.RegistryEntryDisabler.INTEGRATION
        
        # Trigger update
        entity._handle_coordinator_update()
        
        # Verify entity registry update called to ENABLE
        # Note: logic calls update with disabled_by=None
        mock_registry.async_update_entity.assert_called_with(
            entity.entity_id, disabled_by=None
        )
