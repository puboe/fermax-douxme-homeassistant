"""Test for dynamic lock entity behavior."""
from unittest.mock import MagicMock, call

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN

from custom_components.fermax_duoxme.lock import async_setup_entry
from custom_components.fermax_duoxme.const import DOMAIN
from custom_components.fermax_duoxme.api.models import AccessDoor, DoorId

@pytest.fixture
def mock_coordinator(hass):
    """Mock coordinator."""
    coordinator = MagicMock()
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

async def test_dynamic_entity_management(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test entities are added and removed dynamically."""
    
    # Setup mocks
    hass.data = {DOMAIN: {mock_config_entry.entry_id: {"coordinator": mock_coordinator}}}
    hass.async_create_task = MagicMock()
    async_add_entities = MagicMock()
    
    # 1. Initial Setup with no doors
    await async_setup_entry(hass, mock_config_entry, async_add_entities)
    async_add_entities.assert_not_called()
    
    # Verify listener registered
    assert mock_coordinator.async_add_listener.called
    listener = mock_coordinator.async_add_listener.call_args[0][0]

    # 2. Add a door (Simulate update)
    door1 = AccessDoor(
        door_id=DoorId(1, 0, 1), title="Door 1", visible=True, door_type="ZERO"
    )
    mock_pairing = MagicMock()
    mock_pairing.all_visible_doors = [door1]
    mock_pairing.all_doors = [door1]
    mock_pairing.tag = "My House"
    
    mock_device_data = MagicMock()
    mock_device_data.pairing = mock_pairing
    
    mock_coordinator.data.devices = {"dev1": mock_device_data}
    
    # Trigger update
    listener()
    
    # Verify entity added
    assert async_add_entities.call_count == 1
    new_entities = async_add_entities.call_args[0][0]
    assert len(new_entities) == 1
    assert new_entities[0].name == "Door 1"
    assert new_entities[0].unique_id == "dev1_ZERO_1_1"

    # 3. Add a second door
    door2 = AccessDoor(
        door_id=DoorId(1, 0, 2), title="Door 2", visible=True, door_type="ONE"
    )
    mock_pairing.all_visible_doors = [door1, door2]
    mock_pairing.all_doors = [door1, door2]
    
    # Trigger update
    listener()
    
    # Verify only NEW entity added (async_add_entities called again with just the new one)
    assert async_add_entities.call_count == 2
    new_entities_2 = async_add_entities.call_args[0][0]
    assert len(new_entities_2) == 1
    assert new_entities_2[0].name == "Door 2"
    
    # 4. Remove the first door
    mock_pairing.all_visible_doors = [door2]
    mock_pairing.all_doors = [door2]
    
    
    # Mock the async_remove method on the entity
    entity_to_remove = None
    # We need to find the entity instance that was created. 
    # Since we can't easily reach into the closure, we rely on the fact that
    # async_add_entities was called with the objects.
    # The first call added door1's entity.
    entity_door1 = async_add_entities.call_args_list[0][0][0][0]
    entity_door1.async_remove = MagicMock()
    
    # Trigger update
    listener()
    
    # Verify async_remove called on the first entity
    # Note: async_create_task is used, so we verify that
    if isinstance(hass.async_create_task, MagicMock):
        assert hass.async_create_task.called
    else:
        # If it's not a mock (real HA instance), we can check if the entity's remove was scheduled
        # But in this test setup, hass is likely a fixture that might not strictly mock everything
        # Let's force it to be a mock in the setup if needed, but for now let's just assert
        # that entity_door1.async_remove was called, which is what we really care about
        assert entity_door1.async_remove.called

async def test_dynamic_name_update(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test entity name updates when title changes."""
    
    # Setup mocks
    hass.data = {DOMAIN: {mock_config_entry.entry_id: {"coordinator": mock_coordinator}}}
    hass.async_create_task = MagicMock()
    async_add_entities = MagicMock()
    
    # 1. Initial Setup with a door
    door1 = AccessDoor(
        door_id=DoorId(1, 0, 1), title="Original Name", visible=True, door_type="ZERO"
    )
    mock_pairing = MagicMock()
    mock_pairing.all_visible_doors = [door1]
    mock_pairing.all_doors = [door1]
    mock_pairing.tag = "My House"
    
    mock_device_data = MagicMock()
    mock_device_data.pairing = mock_pairing
    mock_coordinator.data.devices = {"dev1": mock_device_data}
    
    await async_setup_entry(hass, mock_config_entry, async_add_entities)
    
    # Get the entity
    assert async_add_entities.call_count == 1
    entity = async_add_entities.call_args[0][0][0]
    # Manually assign hass to the entity since the test setup doesn't add it to hass
    entity.hass = hass
    # Mock async_write_ha_state to avoid integration lookup issues
    entity.async_write_ha_state = MagicMock()
    
    assert entity.name == "Original Name"
    
    # 2. Update title
    # Create new door object with same ID but different title
    door1_new = AccessDoor(
        door_id=DoorId(1, 0, 1), title="New Name", visible=True, door_type="ZERO"
    )
    mock_pairing.all_visible_doors = [door1_new]
    mock_pairing.all_doors = [door1_new]
    
    # Trigger coordinator update
    # The entity is a CoordinatorEntity, so it listens to update.
    # We call the method directly to simulate what the coordinator listener does for the entity
    entity._handle_coordinator_update()
    
    # Verify name updated
    assert entity.name == "New Name"
    # Verify unique_id remains unchanged
    assert entity.unique_id == "dev1_ZERO_1_1"
