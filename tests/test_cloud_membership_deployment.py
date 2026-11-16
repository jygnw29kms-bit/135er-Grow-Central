"""Backend deployments must wait for protected API after Python restart."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_cloud_membership_deploy_checks_python_api_not_static_html():
    script=(ROOT/"scripts/deploy_cloud_membership_backend.sh").read_text()
    assert 'api/v2/collaboration/my-rooms' in script
    assert 'if [[ "$code" == "401" ]]' in script
    assert 'systemctl is-active --quiet "$service"' in script
    assert 'trap rollback ERR' in script
    assert 'cp -p "$backup/cloud_room_membership.py" "$destination"' in script
    assert 'cmp "$source_file" "$destination"' in script
    assert 'chmod 700 "$backup"' in script
    assert "vapid" not in script.lower()
