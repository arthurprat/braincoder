import numpy as np
from .utils.math import log2
import tensorflow as tf


class MutualInformationEstimator(object):

    def __init__(self, model, stimulus_range, omega=None, dof=None):
        self.stimulus_range = np.array(stimulus_range).astype(np.float32)

        if self.stimulus_range.ndim == 1:
            self.stimulus_range = stimulus_range[:, np.newaxis].astype(
                np.float32)

        if self.stimulus_range.shape[1] > 1:
            raise NotImplementedError()

        self.model = model
        self.n_units = self.model.parameters.shape[0]

        self.p_stimulus = 1. / len(self.stimulus_range)

        self.omega = omega
        self.omega_chol = tf.linalg.cholesky(omega).numpy()
        self.dof = dof

        if self.model.weights is None:
            self.weights_ = None
        else:
            self.weights_ = self.model.weights.values[np.newaxis, ...]

    def estimate_mi(self, n=1000):

        resid_dist = self.model.get_residual_dist(
            self.n_units, self.omega_chol, self.dof)

        noise = resid_dist.sample(n)

        predictions = self.model._predict(self.stimulus_range[np.newaxis, ...],
                                          self.model.parameters.values[np.newaxis, ...],
                                          self.weights_)

        # n samples x actual_stimuli x n_voxels
        neural_data = predictions + noise[:, tf.newaxis, :]

        p_stimulus = self.p_stimulus

        p_joint = self.model._likelihood(self.stimulus_range[np.newaxis, :, :],
                                         neural_data,
                                         self.model.parameters.values[np.newaxis, ...],
                                         self.weights_,
                                         self.omega_chol,
                                         self.dof) * p_stimulus

        # n samples x n_simulated x n_hypothetical x n_voxels
        residuals = neural_data[:, :, tf.newaxis, :] - \
            predictions[:, tf.newaxis, :, :]

        p_data = resid_dist.prob(residuals)
        p_data = tf.reduce_sum(p_data, 2) / p_data.shape[2]

        mi = 1. / n * tf.reduce_sum(p_joint *
                                    log2(p_joint / (p_data * p_stimulus)))

        return mi.numpy()
