import pytest
from personal_deadline_radar.fixtures import generate
from personal_deadline_radar.cli import read_inputs
from personal_deadline_radar.core import compute

@pytest.fixture
def fixture_dir(tmp_path):
    generate(tmp_path / "data")
    return tmp_path / "data"

@pytest.fixture
def result(fixture_dir):
    return compute(read_inputs(fixture_dir))
