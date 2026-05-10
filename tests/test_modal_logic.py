
import pytest
from jinja2 import Environment, FileSystemLoader
from squash.models import Profile

def test_modal_player2_selection():
    # Setup Jinja environment to find the template
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('log_match_modal.html')

    # Mock user and profiles
    user = Profile(id="user1", first_name="Alice", last_name="Smith", email="alice@example.com")
    profiles = [
        user,
        Profile(id="user2", first_name="Bob", last_name="Jones", email="bob@example.com")
    ]

    # Render template
    rendered = template.render(
        user=user,
        profiles_for_modal=profiles,
        sessions_for_modal=[]
    )

    # Debugging: Print rendered part of the select
    import re
    player2_select = re.search(r'<select name="player2_id".*?</select>', rendered, re.DOTALL)
    if player2_select:
        print(f"\nDEBUG: Player 2 Select Block:\n{player2_select.group(0)}")
    
    # Assertions
    # Ensure Alice Smith (user1) is disabled in the Player 2 dropdown
    alice_option_p2 = '<option value="user1" disabled'
    assert alice_option_p2 in rendered
    
    # Check that no option in player2_id dropdown is 'selected' (except the placeholder)
    # Extract the block again to count inside it
    if player2_select:
        p2_block = player2_select.group(0)
        p2_selected_count = p2_block.count('selected')
        assert p2_selected_count == 1, f"Expected 1 selected in Player 2 select, found {p2_selected_count}"
        assert 'value="" disabled selected' in p2_block
