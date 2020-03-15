from datetime import datetime, timedelta
import pathlib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class DataPreparation:
    """ Data preparation class.

    This class reads the data in a given path and prepares it
    for further analysis. The given path should contain .csv files
    with stock-market data with at least the following columns:
        - Date
        - Adj close
    
    Each function can be called separately. If all you want is the
    prepared data, simply call 'prepare()'.
    """

    def __init__(self, path: pathlib.Path) -> None:
        """Initialisation"""

        self.path = path
        self.data = self.read_data(self.path)
        self.summary = self.summarise(self.data)

    def read_data(self, path: pathlib.Path) -> dict:
        """Read all the data in a given folder. 
        
        Read all the data in a given directory in a Pathlib format
        and return a python dictionary. The key corresponds to the
        index and the item corresponds to the pandas DataFrame.
        """

        # List sources
        data_sources = [x for x in path.iterdir() if "sources" not in str(x)]

        # Indices
        indices = []
        for source in data_sources:
            start = str(source).find("^")
            stop = str(source).find(".csv")

            indices.append(str(source)[start + 1 : stop])

        dataframes = {}
        dataframes.update(
            {
                indices[ix]: pd.read_csv(source, index_col=0)
                for ix, source in enumerate(data_sources)
            }
        )

        for key, data in dataframes.items():
            data.index = [datetime.strptime(ix, "%Y-%m-%d") for ix in data.index]
            dataframes[key] = data

        return dataframes

    def summarise(self, dataframes: dict) -> pd.DataFrame:
        """Summarise the available data.
        
        Returns a pandas DataFrame with a summary of the available 
        data. The returned DataFrame will have the indices of which
        the data is available on the index. The columns will contain
        information on the first date (First), last date (Last), 
        lowest close (Min) and highest close (Max).
        """

        summary = {"Index": [], "First": [], "Last": [], "Min": [], "Max": []}

        for index in dataframes:
            df = dataframes[index]

            summary["Index"].append(index)
            summary["First"].append(min(df.index))
            summary["Last"].append(max(df.index))
            summary["Min"].append(min(df["Adj Close"].values))
            summary["Max"].append(max(df["Adj Close"].values))

        return pd.DataFrame.from_dict(summary).set_index("Index")

    def determine_change(
        self, dataframe: pd.DataFrame, clean: bool = True
    ) -> pd.DataFrame:
        """Determine the change between subsequent dates.
        
        Add a column 'Change' to the given dataframe. This is the 
        change between two subsequent 'adjusted closes' in percentages.
        If 'clean' == True, the values without data will be filled with
        by linearly interpolating between the surrounding datapoints.
        """

        closes = dataframe["Adj Close"].values
        changes = [0]

        for ix, new in enumerate(closes[1::]):
            old = closes[ix]
            changes.append((new - old) / old * 100)

        dataframe["Change"] = changes

        if clean:
            dataframe.interpolate(method="linear", inplace=True)

        return dataframe

    def biggest_changes(self, dataframes: dict, percentile: float) -> dict:
        """Determine the biggest changes.

        Determine the biggest changes for a given percentile
        for each of the given DataFrames in the given dictionary and
        return a dictionary with nested dictionaries. The keys of the
        dictionary correspond to the given indices. The nested dictionary
        has the keys Data, P and Dates. With corresponding items respectively
        array with the sorted changes, value for the given percentile and the
        dates on which the larges changes occured.
        
        If the given percentile is equal to or below 50, the largest 
        negative changes are returned. If the given percentile is 
        above 50, the largest positive changes are returned.
        """

        changes = {}
        changes.update(
            {
                ix: {"Data": np.sort(data.Change.values)}
                for ix, data in dataframes.items()
            }
        )

        for key in changes:
            P = np.percentile(changes[key]["Data"], percentile)
            df = dataframes[key]

            if percentile <= 50:
                df = df[df["Change"] <= P]
            else:
                df = df[df["Change"] > P]

            changes[key][f"P{percentile}"] = P
            changes[key]["Dates"] = df.index

        return changes

    def determine_effect(
        self, dataframe: pd.DataFrame, changes: dict, index: str
    ) -> dict:
        """Check the effect of the given changes.
        
        Check the effect of the large declines or rises of the index
        after a specified timeframe. The effect is determined after 
        1 day, 1 week, 1 month, 3 months, 6 months and 1 year.
        """

        # Lists to return
        effect = {
            "Index": [],
            "Date": [],
            "Close": [],
            "Drop": [],
            "1D": [],
            "1W": [],
            "4W": [],
            "12W": [],
            "26W": [],
            "52W": [],
        }

        # Scroll through all the dates
        for date in changes["Dates"]:

            # Save the data we have
            effect["Index"].append(index)
            effect["Date"].append(date)
            effect["Close"].append(dataframe.loc[date, "Adj Close"])
            effect["Drop"].append(dataframe.loc[date, "Change"])

            new_dates = []

            # After 1 day
            new_dates.append(("1D", date + timedelta(days=1)))

            # After x weeks
            for week in [1, 4, 12, 26, 52]:
                new_dates.append((f"{week}W", date + timedelta(days=week * 7)))

            # Check if date is available in dateframe
            for date in new_dates:
                date_found = False
                add = 0

                # date is available
                if date[1] <= dataframe.index[-1]:
                    while not date_found:
                        try:
                            ix = date[1] + timedelta(days=add)
                            new = dataframe.loc[ix, "Adj Close"]

                            if new == 0:
                                add += 1
                            else:
                                date_found = True

                        except:
                            add += 1

                    old = effect["Close"][-1]
                    effect[date[0]].append((new - old) / old * 100)

                # date is not available
                else:
                    effect[date[0]].append("N/A")

        return effect

    def update_effects(self, effects: dict, effect: dict) -> dict:
        """ Update the dictionary by given data. """

        assert (
            effects.keys() == effect.keys()
        ), "Something went wrong, the keys of the given dictionaries are not the same"

        for key in effects:
            effects[key].extend(effect[key])

        return effects

    def check_effect(
        self, dataframes: dict, changes: dict, index: str = "All"
    ) -> pd.DataFrame:
        """Check the effect of the given changes.
        
        Check the effect of the large declines or rises of the index
        after a specified timeframe. The effect is determined after 
        1 day, 1 week, 1 month, 3 months, 6 months and 1 year.
        
        The given dictionaries dataframes and changes should 
        correspond to the dictionaries as returned by the 
        functions 'read_data' and 'biggest_changes'. 
        
        If index is not set to 'All' only a pandas DataFrame of the
        given index is returned. If index is set to 'All' a pandas 
        DataFrame with all available information is returned.
        """

        effects = {
            "Index": [],
            "Date": [],
            "Close": [],
            "Drop": [],
            "1D": [],
            "1W": [],
            "4W": [],
            "12W": [],
            "26W": [],
            "52W": [],
        }

        if index != "All":
            effect = self.determine_effect(dataframes[index], changes[index], index)
            effects = self.update_effects(effects, effect)

        # For all indices
        for index in dataframes.keys():
            effect = self.determine_effect(dataframes[index], changes[index], index)
            effects = self.update_effects(effects, effect)

        return pd.DataFrame.from_dict(effects)

    def prepare(self, percentile: float, index: str = "All") -> pd.DataFrame:
        """Prepare the data.
        
        Returns a dataframe with the effect of the large declines 
        or rises of the index after a specified timeframe. The 
        effect is determined after 1 day, 1 week, 1 month, 3 months, 
        6 months and 1 year.

        If the given percentile is equal to or below 50, the largest 
        negative changes are returned. If the given percentile is 
        above 50, the largest positive changes are returned.
        """

        # Make sure input is correct
        if index != "All":
            assert (
                index in self.summary.index
            ), "The specified index is not available in the data"
        assert 0 < percentile <= 100, "Specify a percentile in the interval (0, 100]"

        # Add change column to available data
        for key, data in self.data.items():
            self.data[key] = self.determine_change(data)

        # Determine the changes corresponding to the given percentile
        self.changes = self.biggest_changes(self.data, percentile)

        # Determine the effect of these changes
        return self.check_effect(self.data, self.changes, index)
