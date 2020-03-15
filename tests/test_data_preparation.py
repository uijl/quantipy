import pathlib
from quantipy.analysis import DataPreparation

def test_read_data():
    """Test the DataPreparation class."""

    path = pathlib.Path.cwd()
    test_class = DataPreparation(path.joinpath("data"))

    test_class.prepare(percentile = 0.5)