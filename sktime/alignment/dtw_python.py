# -*- coding: utf-8 -*-
"""Interface module to dtw-python package.

Exposes basic interface, excluding multivariate case.
"""

__author__ = ["fkiraly"]

import pandas as pd
import numpy as np

from sktime.utils.validation._dependencies import _check_soft_dependencies
from sktime.alignment._base import BaseAligner

_check_soft_dependencies("dtw")


class AlignerDTW(BaseAligner):
    """Aligner interface for dtw-python.

    Behaviour: computes the full alignment between X[0] and X[1]
        assumes pairwise alignment (only two series) and univariate
        if multivariate sequences are passed:
            alignment is computed on univariate series with variable_to_align;
            if this is not set, defaults to the first variable of X is used
        raises an error if variable_to_align is not present in X[0] or X[1]

    Parameters
    ----------
    dist_method: string, pointwise (local) distance function to use
        one of the functions in `scipy.spatial.distance.cdist`
        default = 'euclidean'
    step_pattern: a stepPattern object describing the local warping steps
        one of: 'symmetric1', 'symmetric2' (default), 'asymmetric',
                and dozens of other more non-standard step patterns;
                list can be displayed by calling help(stepPattern) in dtw
    window_type: string, the chosen windowing function
        "none", "itakura", "sakoechiba", or "slantedband"
            "none" (default) - no windowing
            "sakoechiba" - a band around main diagonal
            "slantedband" - a band around slanted diagonal
            "itakura" - Itakura parallelogram
    open_begin, open_end: boolean; whether to perform open-ended alignments
        open_begin = whether alignment open ended at start (low index)
        open_end = whether alignment open ended at end (high index)
    variable_to_align: string; which variable to use for univariate alignment
        default: first variable in X as passed to fit
    """

    _tags = {
        "capability:multiple-alignment": False,  # can align more than two sequences?
        "capability:distance": True,  # does compute/return overall distance?
        "capability:distance-matrix": True,  # does compute/return distance matrix?
    }

    def __init__(
        self,
        dist_method="euclidean",
        step_pattern="symmetric2",
        window_type="none",
        open_begin=False,
        open_end=False,
        variable_to_align=None,
    ):
        """Construct instance."""
        super(AlignerDTWdist, self).__init__()

        self.dist_method = dist_method
        self.step_pattern = step_pattern
        self.window_type = window_type
        self.open_begin = open_begin
        self.open_end = open_end
        self.variable_to_align = variable_to_align

    def _fit(self, X, Z=None):
        """Fit alignment given series/sequences to align.

            core logic

        Parameters
        ----------
        X: list of pd.DataFrame (sequence) of length n - panel of series to align
        Z: pd.DataFrame with n rows, optional; metadata, row correspond to indices of X

        Writes to self
        --------------
        alignment - computed alignment from dtw package
        X - reference to input X
        """
        # soft dependency import of dtw
        from dtw import dtw

        # these variables from self are accessed
        dist_method = self.dist_method
        step_pattern = self.step_pattern
        window_type = self.window_type
        open_begin = self.open_begin
        open_end = self.open_end

        # shorthands for 1st and 2nd sequence
        X1 = X[0]
        X2 = X[1]

        # retrieve column to align from data frames, convert to np.array
        var_to_align = self.variable_to_align
        if var_to_align is None:
            var_to_align = X1.columns.values[0]

        if var_to_align not in X1.columns.values:
            raise ValueError(
                f"X[0] does not have variable {var_to_align} used for alignment"
            )
        if var_to_align not in X2.columns.values:
            raise ValueError(
                f"X[1] does not have variable {var_to_align} used for alignment"
            )

        X1vec = X1[var_to_align].values
        X2vec = X2[var_to_align].values

        # pass to the interfaced dtw function and store to self
        alignment = dtw(
            X1vec,
            X2vec,
            dist_method=dist_method,
            step_pattern=step_pattern,
            window_type=window_type,
            open_begin=open_begin,
            open_end=open_end,
            keep_internals=True,
        )

        self.alignment = alignment
        self.X = X
        self.variable_to_align = var_to_align  # changed only if was None

        return self

    def get_alignment(self):
        """Return alignment for sequences/series passed in fit (iloc indices).

        Behaviour: returns an alignment for sequences in X passed to fit
            model should be in fitted state, fitted model parameters read from self

        Returns
        -------
        pd.DataFrame in alignment format, with columns 'ind'+str(i) for integer i
            cols contain iloc index of X[i] mapped to alignment coordinate for alignment
        """
        # retrieve alignment
        alignment = self.alignment

        # convert to required data frame format and return
        aligndf = pd.DataFrame({"ind0": alignment.index1, "ind1": alignment.index2})

        return aligndf

    def get_distance(self):
        """Return overall distance of alignment.

        Behaviour: returns overall distance corresponding to alignment
            not all aligners will return or implement this (optional)

        Returns
        -------
        distance: float - overall distance between all elements of X passed to fit
        """
        return self.alignment.distance

    def get_distance_matrix(self):
        """Return distance matrix of alignment.

        Behaviour: returns pairwise distance matrix of alignment distances
            not all aligners will return or implement this (optional)

        Returns
        -------
        distmat: an (n x n) np.array of floats, where n is length of X passed to fit
            [i,j]-th entry is alignment distance between X[i] and X[j] passed to fit
        """
        # since dtw does only pairwise alignments, this is always
        distmat = np.zeros((2, 2), dtype="float")
        distmat[0, 1] = self.alignment.distance
        distmat[1, 0] = self.alignment.distance

        return distmat


class AlignerDTWdist(BaseAligner):
    """Aligner interface for dtw-python using pairwise transformer.

        uses transformer for computation of distance matrix passed to alignment

    Components
    ----------
    dist_trafo: estimator following the pairwise transformer template
        i.e., instance of concrete class implementing template BasePairwiseTransformer

    Parameters
    ----------
    step_pattern: a stepPattern object describing the local warping steps
        one of: 'symmetric1', 'symmetric2' (default), 'asymmetric',
                and dozens of other more non-standard step patterns;
                list can be displayed by calling help(stepPattern) in dtw
    window_type: string, the chosen windowing function
        "none", "itakura", "sakoechiba", or "slantedband"
            "none" (default) - no windowing
            "sakoechiba" - a band around main diagonal
            "slantedband" - a band around slanted diagonal
            "itakura" - Itakura parallelogram
    open_begin, open_end: boolean; whether to perform open-ended alignments
        open_begin = whether alignment open ended at start (low index)
        open_end = whether alignment open ended at end (high index)
    """

    _tags = {
        "capability:multiple-alignment": False,  # can align more than two sequences?
        "capability:distance": True,  # does compute/return overall distance?
        "capability:distance-matrix": True,  # does compute/return distance matrix?
    }

    def __init__(
        self,
        dist_trafo=None,
        step_pattern="symmetric2",
        window_type="none",
        open_begin=False,
        open_end=False,
    ):
        """Construct instance."""
        super(AlignerDTWdist, self).__init__()

        if dist_trafo is None:
            raise ValueError("No component dist_trafo provided")
        else:
            self.dist_trafo = dist_trafo

        self.step_pattern = step_pattern
        self.window_type = window_type
        self.open_begin = open_begin
        self.open_end = open_end

    def _fit(self, X, Z=None):
        """Fit alignment given series/sequences to align.

            core logic

        Parameters
        ----------
        X: list of pd.DataFrame (sequence) of length n - panel of series to align
        Z: pd.DataFrame with n rows, optional; metadata, row correspond to indices of X

        Writes to self
        --------------
        alignment - computed alignment from dtw package
        X - reference to input X
        """
        # soft dependency import of dtw
        from dtw import dtw

        # these variables from self are accessed
        dist_trafo = self.dist_trafo
        step_pattern = self.step_pattern
        window_type = self.window_type
        open_begin = self.open_begin
        open_end = self.open_end

        # shorthands for 1st and 2nd sequence
        X1 = X[0]
        X2 = X[1]

        # compute distance matrix using cdist
        distmat = dist_trafo(X1, X2)

        # pass to the interfaced dtw function and store to self
        alignment = dtw(
            distmat,
            step_pattern=step_pattern,
            window_type=window_type,
            open_begin=open_begin,
            open_end=open_end,
            keep_internals=True,
        )

        self.alignment = alignment
        self.X = X

        return self

    def get_alignment(self):
        """Return alignment for sequences/series passed in fit (iloc indices).

        Behaviour: returns an alignment for sequences in X passed to fit
            model should be in fitted state, fitted model parameters read from self

        Returns
        -------
        pd.DataFrame in alignment format, with columns 'ind'+str(i) for integer i
            cols contain iloc index of X[i] mapped to alignment coordinate for alignment
        """
        # retrieve alignment
        alignment = self.alignment

        # convert to required data frame format and return
        aligndf = pd.DataFrame({"ind0": alignment.index1, "ind1": alignment.index2})

        return aligndf

    def get_distance(self):
        """Return overall distance of alignment.

        Behaviour: returns overall distance corresponding to alignment
            not all aligners will return or implement this (optional)

        Returns
        -------
        distance: float - overall distance between all elements of X passed to fit
        """
        return self.alignment.distance

    def get_distance_matrix(self):
        """Return distance matrix of alignment.

        Behaviour: returns pairwise distance matrix of alignment distances
            not all aligners will return or implement this (optional)

        Returns
        -------
        distmat: an (n x n) np.array of floats, where n is length of X passed to fit
            [i,j]-th entry is alignment distance between X[i] and X[j] passed to fit
        """
        # since dtw does only pairwise alignments, this is always
        distmat = np.zeros((2, 2), dtype="float")
        distmat[0, 1] = self.alignment.distance
        distmat[1, 0] = self.alignment.distance

        return distmat