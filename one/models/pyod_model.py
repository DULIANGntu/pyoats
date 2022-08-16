from typing import Any

import numpy as np
import numpy.typing as npt
from darts.timeseries import TimeSeries
from darts.dataprocessing.transformers import Scaler
from scipy.stats import zscore
from numpy.lib.stride_tricks import sliding_window_view
import optuna

from one.models.base import Model


class PyODModel(Model):
    def __init__(self, model_cls, window: int = 10, **kwargs):
        self.window = window

        self.model_cls = model_cls
        self.model = model_cls(**kwargs)
        self.scaler = None

    @property
    def model_name(self):
        return type(self).__name__

    def __repr__(self):
        r = {}
        r.update({"model_name": self.model_name})
        r.update({"window": self.window})

        return str(r)

    def fit(self, train_data: npt.NDArray[Any], **kwargs):
        windows = self._get_window(train_data)
        self.model.fit(windows)

    def get_scores(self, test_data: npt.NDArray[Any]):
        # Multivar
        multivar = True if test_data.ndim > 1 and test_data.shape[1] > 1 else False

        windows = self._get_window(test_data)
        scores = self.model.decision_function(windows)
        scores = np.abs(zscore(scores))

        scores = np.append(np.zeros(self.window-1), scores)
        if multivar: scores = np.tile(scores, (test_data.shape[1], 1)).T

        return scores
        

    def _get_window(self, data):
        # Univariate in 2-D
        data = self._scale_series(data)
        if data.ndim > 1 and data.shape[1] == 1:
            data = data.flatten()

        # Multivar
        multivar = True if data.ndim > 1 and data.shape[1] > 1 else False


        windows = sliding_window_view(data, self.window, axis=0)

        if multivar:
            n_samples, feats, n_t = windows.shape
            windows = windows.reshape(n_samples, n_t * feats)
        return windows

    def _scale_series(self, series):
        series = TimeSeries.from_values(series)

        if self.scaler is None:
            self.scaler = Scaler()
            self.scaler.fit(series)

        series = self.scaler.transform(series)

        return series.pd_dataframe().to_numpy().astype(np.float32)