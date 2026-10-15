import asyncio

from app import recipes, timelapse


def test_recipe_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(recipes, "DATA_FILE", tmp_path / "recipes.json")
    monkeypatch.setattr(recipes, "append_audit", lambda *args, **kwargs: None)
    body = recipes.RecipeDefinition(name="Bl?te Woche 3", phase="flowering", target_temperature_c=25.0, target_humidity_percent=50, target_vpd_kpa=1.3, light_cycle="12/12", watering_note="nach Bedarf", notes="Test")
    created = asyncio.run(recipes.create_recipe(body))
    recipe_id = created["recipe"]["id"]
    listed = asyncio.run(recipes.list_recipes())
    assert listed["execution_status"] == "declarative_only"
    assert listed["recipes"][0]["id"] == recipe_id
    updated = asyncio.run(recipes.update_recipe(recipe_id, body.model_copy(update={"name": "Bl?te Woche 4"})))
    assert updated["recipe"]["name"] == "Bl?te Woche 4"
    assert asyncio.run(recipes.delete_recipe(recipe_id))["ok"] is True
    assert asyncio.run(recipes.list_recipes())["recipes"] == []


def test_timelapse_capture_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(timelapse, "ROOT", tmp_path / "timelapse")
    monkeypatch.setattr(timelapse, "MAX_RUNS", 5)
    monkeypatch.setattr(timelapse, "job", timelapse._Job())
    monkeypatch.setattr(timelapse, "append_audit", lambda *args, **kwargs: None)

    async def no_stream(_reason):
        return False

    async def no_sleep(_seconds):
        return None

    def snapshot(_camera_id, _width, _height):
        return b"\xff\xd8fakejpeg\xff\xd9", "cam-1", "/dev/video0", {"width": 640, "height": 480}

    monkeypatch.setattr(timelapse, "_stop_active_stream", no_stream)
    monkeypatch.setattr(timelapse, "_snapshot_sync", snapshot)
    monkeypatch.setattr(timelapse.asyncio, "sleep", no_sleep)

    async def scenario():
        started = await timelapse.start(timelapse.StartBody(interval_seconds=15, max_frames=2))
        assert started["active"] is True
        task = timelapse.job.task
        await task
        rows = await timelapse.runs()
        assert len(rows["runs"]) == 1
        assert rows["runs"][0]["frames"] == 2
        run_id = rows["runs"][0]["run_id"]
        assert (timelapse.ROOT / run_id / "frame_00001.jpg").is_file()
        assert (timelapse.ROOT / run_id / "frame_00002.jpg").is_file()
        assert timelapse.job.task is None

    asyncio.run(scenario())
