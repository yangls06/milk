# -*- coding: utf-8 -*-
# Copyright (C) 2008-2011, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# LICENSE: MIT

from __future__ import division
from ..supervised.classifier import normaliselabels
import numpy as np

__all__ = ['foldgenerator', 'getfold', 'nfoldcrossvalidation']
def foldgenerator(labels, nfolds=None, origins=None):
    '''
    for train,test in foldgenerator(labels, nfolds=None, origins=None)
        ...

    This generator breaks up the data into `n` folds (default 10).

    If `origins` is given, then all elements that share the same origin will
    either be in testing or in training (never in both).  This is useful when
    you have several replicates that shouldn't be mixed together between
    training&testing but that can be otherwise be treated as independent for
    learning.

    Parameters
    ----------
    labels : a sequence
        the labels
    nfolds : integer
        nr of folds (default 10 or minimum label size)
    origins : if present, must be an array of indices of the same size as labels.

    Returns
    -------
    iterator over `train, test`, two boolean arrays
    '''
    labels,names = normaliselabels(labels)
    if origins is None:
        origins = np.arange(len(labels))
    else:
        if len(origins) != len(labels):
            raise ValueError(
             'milk.nfoldcrossvalidation.foldgenerator: origins must be of same size as labels')
        origins = np.asanyarray(origins)
    fmin = len(labels)
    for lab in set(labels):
        curmin = len(set(origins[labels == lab]))
        fmin = min(fmin, curmin)

    if fmin == 1:
        raise ValueError('''
milk.nfoldcrossvalidation.foldgenerator: nfolds was reduced to 1 because minimum class size was 1.
If you passed in an origins parameter, it might be caused by having a class come from a single origin.
''')

    fold = np.zeros(len(labels))
    fold -= 1

    if nfolds is None:
        nfolds = min(fmin, 10)
    elif nfolds > fmin:
        from warnings import warn
        warn('milk.measures.nfoldcrossvalidation: Reducing the nr. of folds from %s to %s (minimum class size).' % (nfolds, fmin))
        nfolds = fmin

    for lab in set(labels):
        locations = (labels == lab)
        usedorigins = np.unique(origins[locations])
        weights = np.array([np.sum(origins == orig) for orig in usedorigins])
        foldweight = np.zeros(nfolds, int)
        for w,orig in sorted(zip(weights, usedorigins)):
            f = np.argmin(foldweight)
            if np.any(fold[origins == orig] > -1):
                raise ValueError(
                        'milk.nfoldcrossvalidation.foldgenerator: something is wrong. Maybe origin %s is present in two labels.' % orig)
            fold[origins == orig] = f
            foldweight[f] += w

    for f in xrange(nfolds):
        yield (fold != f), (fold == f)

def getfold(labels, fold, nfolds=None, origins=None):
    '''
    trainingset,testingset = getfold(labels, fold, nfolds=None, origins=None)

    Get the training and testing set for fold `fold` in `nfolds`

    Arguments are the same as for `foldgenerator`

    Parameters
    ----------
    labels : ndarray of labels
    fold : integer
    nfolds : integer
        number of folds (default 10 or size of smallest class)
    origins : sequence, optional
        if given, then objects with same origin are *not* scattered across folds
    '''
    if nfolds < fold:
        raise ValueError('milk.getfold: Attempted to get fold %s out of %s' % (fold, nfolds))
    for i,(t,s) in enumerate(foldgenerator(labels, nfolds, origins)):
        if i == fold:
            return t,s
    raise ValueError('milk.getfold: Attempted to get fold %s but the number of actual folds was too small (%s)' % (fold,i))

def nfoldcrossvalidation(features, labels, nfolds=None, classifier=None, origins=None, return_predictions=False):
    '''
    Perform n-fold cross validation

    cmatrix,names = nfoldcrossvalidation(features, labels, nfolds=10, classifier={defaultclassifier()}, origins=None, return_predictions=False)
    cmatrix,names,predictions = nfoldcrossvalidation(features, labels, nfolds=10, classifier={defaultclassifier()}, origins=None, return_predictions=True)

    cmatrix will be a N x N matrix, where N is the number of classes

    cmatrix[i,j] will be the number of times that an element of class i was
    classified as class j

    names[i] will correspond to the label name of class i

    Parameters
    ----------
    features : a sequence
    labels : an array of labels, where label[i] is the label corresponding to features[i]
    nfolds : integer, optional
        Nr of folds. Default: 10
    classifier : learner object, optional
        classifier should implement the train() method to return a model
        (something with an apply() method). defaultclassifier() by default

    origins : sequence, optional
        Origin ID (see foldgenerator)
    return_predictions : bool, optional
        whether to return predictions (default: False)

    Returns
    -------
    cmatrix : ndarray
        confusion matrix
    names : sequence
        sequence of labels so that cmatrix[i,j] corresponds to names[i], names[j]
    predictions : sequence
        predicted output for each element
    '''
    import operator
    from .measures import confusion_matrix
    if len(features) != len(labels):
        raise ValueError('milk.measures.nfoldcrossvalidation: len(features) should match len(labels)')
    if classifier is None:
        from ..supervised.defaultclassifier import defaultclassifier
        classifier = defaultclassifier()
    labels,names = normaliselabels(labels)
    if return_predictions:
        predictions = np.empty_like(labels)
        predictions.fill(-1) # This makes it clearer if there are bugs in the programme

    features = np.asanyarray(features)

    nclasses = labels.max() + 1
    results = []
    measure = confusion_matrix
    for trainingset,testingset in foldgenerator(labels, nfolds, origins=origins):
        model = classifier.train(features[trainingset], labels[trainingset])
        cur_predictions = [model.apply(f) for f in features[testingset]]
        if return_predictions:
            predictions[testingset] = np.array(cur_predictions, dtype=predictions.dtype)
        results.append(measure(labels[testingset], cur_predictions))

    result = reduce(operator.add, results)
    if return_predictions:
        return result, names, predictions
    return result, names

