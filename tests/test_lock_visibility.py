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
    
    # We need to capture the listener callback
    listener_callback = None
    def mock_add_listener(callback):
        nonlocal listener_callback
        listener_callback = callback
        return MagicMock()
        
    mock_coordinator.async_add_listener.side_effect = mock_add_listener
    
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
    entity.entity_id = "lock.test_door"  # Set ID so logic works
    entity.async_write_ha_state = MagicMock()
    
    # Verify initially available
    
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
        # Trigger update via global listener
        assert listener_callback is not None
        listener_callback()
        
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
        listener_callback()
        
        # Verify entity registry update called to ENABLE
        # Note: logic calls update with disabled_by=None
        mock_registry.async_update_entity.assert_called_with(
            entity.entity_id, disabled_by=None
        )

async def test_initial_visibility_state(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test initial visibility state (entity_registry_enabled_default)."""
    
    # Setup mocks
    hass.data = {DOMAIN: {mock_config_entry.entry_id: {"coordinator": mock_coordinator}}}
    async_add_entities = MagicMock()
    
    # Setup with an INVISIBLE door
    door_hidden = AccessDoor(
        door_id=DoorId(1, 0, 1), title="Hidden Door", visible=False, door_type="ZERO"
    )
    mock_pairing = MagicMock()
    mock_pairing.all_doors = [door_hidden]
    mock_pairing.tag = "My House"
    
    mock_device_data = MagicMock()
    mock_device_data.pairing = mock_pairing
    mock_coordinator.data.devices = {"dev1": mock_device_data}
    
    await async_setup_entry(hass, mock_config_entry, async_add_entities)
    
    assert async_add_entities.call_count == 1
    entity = async_add_entities.call_args[0][0][0]
    
    # Verify entity_registry_enabled_default property
    # It should be False because visible=False
    assert entity.entity_registry_enabled_default is False

    # Check a visible door too
    door_visible = AccessDoor(
        door_id=DoorId(2, 0, 2), title="Visible Door", visible=True, door_type="ONE"
    )
    mock_pairing.all_doors = [door_visible] 
    
    # Reset and call again to generate new entity
    mock_coordinator.data.devices["dev1"].pairing.all_doors = [door_visible]
    
    # We clear known entities by mocking a new entry setup or just checking a new entity instance
    # The simplest way is to manually instantiate the class or reset the setup
    # But async_setup_entry creates local variables.
    # Let's just create the entity manually to verify the class property behavior if we want, 
    # or re-run setup with a new door.
    
    # Only the first batch is added. Let's create a new list for setup
    # But since we want to test the class logic which is what matters:
    from custom_components.fermax_duoxme.lock import FermaxLock
    
    entity_visible = FermaxLock(mock_coordinator, "dev1", door_visible, "My House")
    assert entity_visible.entity_registry_enabled_default is True

async def test_automatic_reenable(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test that disabled entities are automatically re-enabled when they become visible."""
    
    # 1. Setup with INVISIBLE door
    door_hidden = AccessDoor(
        door_id=DoorId(1, 0, 1), title="Door 1", visible=False, door_type="ZERO"
    )
    mock_pairing = MagicMock()
    mock_pairing.all_doors = [door_hidden]
    mock_pairing.tag = "My House"
    
    mock_device_data = MagicMock()
    mock_device_data.pairing = mock_pairing
    mock_coordinator.data.devices = {"dev1": mock_device_data}
    
    # Setup hass.data
    hass.data = {DOMAIN: {mock_config_entry.entry_id: {"coordinator": mock_coordinator}}}

    async_add_entities = MagicMock()
    
    # Mock registry
    mock_registry = MagicMock()
    mock_registry_entry = MagicMock()
    mock_registry_entry.disabled_by = er.RegistryEntryDisabler.INTEGRATION
    mock_registry.async_get.return_value = mock_registry_entry
    
    # We need to capture the listener callback
    listener_callback = None
    def mock_add_listener(callback):
        nonlocal listener_callback
        listener_callback = callback
        return MagicMock()
        
    mock_coordinator.async_add_listener.side_effect = mock_add_listener
    
    with unittest.mock.patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_registry):
        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        assert async_add_entities.call_count == 1
        # Confirm we captured the listener
        assert listener_callback is not None
        
        entity = async_add_entities.call_args[0][0][0]
        entity.entity_id = "lock.test_door_2"

        # 2. Update to VISIBLE
        door_visible = AccessDoor(
            door_id=DoorId(1, 0, 1), title="Door 1", visible=True, door_type="ZERO"
        )
        mock_pairing.all_doors = [door_visible]
        
        # Trigger the global listener (not the entity listener)
        listener_callback()
        
        # 3. Verify registry update
        # Use any_call to find the registry update among potential other calls
        mock_registry.async_update_entity.assert_called_with(
            async_add_entities.call_args[0][0][0].entity_id, disabled_by=None
        )
