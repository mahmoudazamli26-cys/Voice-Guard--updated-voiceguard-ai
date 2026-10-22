"""Metrics use fake=positive; calibration is separate from held-out testing."""
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_curve, roc_auc_score


def metrics(labels, scores):
    y, p = np.asarray(labels), np.asarray(scores)
    if set(y.tolist()) != {0,1} or not np.isfinite(p).all():
        raise ValueError('Metrics require finite scores and both real and fake labels')
    predicted = (p >= 0.5).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y, predicted, average='binary', zero_division=0)
    fpr, tpr, thresholds = roc_curve(y, p)
    fnr = 1 - tpr
    delta = fpr - fnr
    high = int(np.flatnonzero(delta >= 0)[0])
    if high == 0:
        eer = float(fpr[0])
    else:
        low = high - 1
        fraction = -delta[low] / (delta[high] - delta[low])
        eer = float(fpr[low] + fraction * (fpr[high] - fpr[low]))
    return {'count':len(y),'real_count':int(sum(y==0)),'fake_count':int(sum(y==1)),
            'diagnostic_threshold':0.5, 'accuracy':float(accuracy_score(y,predicted)),
            'precision':float(precision),'recall':float(recall),'f1':float(f1),
            'confusion_matrix_real_fake':confusion_matrix(y,predicted,labels=[0,1]).tolist(),
            'roc_auc':float(roc_auc_score(y,p)), 'eer_interpolated':eer,
            'roc':{'fpr':fpr.tolist(),'tpr':tpr.tolist(),
                   'thresholds':[float(x) if np.isfinite(x) else None for x in thresholds]}}


def calibrate(labels, scores, max_error=0.05, min_per_class=20):
    y, p = np.asarray(labels), np.asarray(scores)
    if not 0 <= max_error < 0.5 or set(y.tolist()) != {0,1}:
        raise ValueError('Calibration requires both labels and max_error in [0,0.5)')
    if min(sum(y==0), sum(y==1)) < min_per_class:
        raise ValueError(f'Calibration requires at least {min_per_class} examples per class')
    points = np.unique(np.r_[0, p, 1])
    candidates = np.unique(np.r_[points, (points[1:] + points[:-1])/2])
    if len(candidates)>256:
        candidates = np.unique(np.quantile(candidates, np.linspace(0,1,256)))
    real_candidates = [float(t) for t in candidates if np.mean(p[y==1]<=t)<=max_error]
    fake_candidates = [float(t) for t in candidates if np.mean(p[y==0]>=t)<=max_error]
    best = None
    for lower in real_candidates:
        for upper in fake_candidates:
            if lower >= upper:
                continue
            coverage = float(np.mean((p<=lower)|(p>=upper)))
            if best is None or (coverage,upper-lower)>(best[0],best[2]-best[1]):
                best=(coverage,lower,upper)
    if best is None:
        raise ValueError('No valid abstention thresholds satisfy the validation error constraint')
    return {'real_threshold':best[1],'fake_threshold':best[2], 'validation_coverage':best[0],
            'max_empirical_class_error':max_error,'validation_count':len(y),
            'warning':'Empirical validation constraints do not guarantee future error rates.'}


def decision_metrics(labels, scores, calibration, eligible=None):
    y, p=np.asarray(labels),np.asarray(scores)
    if y.ndim != 1 or y.shape != p.shape or set(y.tolist()) != {0, 1} or not np.isfinite(p).all():
        raise ValueError('Decision metrics require matching finite scores and both labels')
    permitted = np.ones(len(y), dtype=bool) if eligible is None else np.asarray(eligible, dtype=bool)
    if permitted.shape != y.shape:
        raise ValueError('Eligibility mask must match the recordings')
    real=(p<=calibration['real_threshold'])&permitted
    fake=(p>=calibration['fake_threshold'])&permitted;decided=real|fake
    return {'count':len(y), 'decided_count':int(sum(decided)),
            'coverage':float(np.mean(decided)), 'inconclusive_count':int(sum(~decided)),
            'decided_accuracy':float(np.mean(fake[decided]==y[decided])) if decided.any() else None,
            'false_fake_rate':float(np.mean(fake[y==0])),
            'false_real_rate':float(np.mean(real[y==1])),
            'speech_gate_abstentions':int(sum(~permitted)),
            'confusion_real_fake_inconclusive':[
                [int(sum(real&(y==label))),int(sum(fake&(y==label))),int(sum(~decided&(y==label)))]
                for label in [0,1]]}
