"""Tracking metrics (MOTA, IDF1, identity switches) and event-level precision/recall for the zone and dwell rules.

MOTA follows CLEAR-MOT (Bernardin & Stiefelhagen 2008) and IDF1 follows Ristani et al. (2016); both are computed
here directly because motmetrics does not run on NumPy 2.
"""
import csv
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment


def load_mot(path, is_gt=False):
    """MOTChallenge text: frame,id,x,y,w,h,flag,... For ground truth (CVAT 'MOT 1.1'), flag 0 marks ignored boxes."""
    frames = defaultdict(list)
    for line in open(path, encoding="utf-8"):
        p = line.strip().split(",")
        if len(p) < 6:
            continue
        if is_gt and len(p) > 6 and float(p[6]) == 0:
            continue
        x, y, w, h = map(float, p[2:6])
        frames[int(float(p[0]))].append((int(float(p[1])), (x, y, x + w, y + h)))
    return frames


def iou_matrix(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ix1 = np.maximum(a[:, None, 0], b[None, :, 0]); iy1 = np.maximum(a[:, None, 1], b[None, :, 1])
    ix2 = np.minimum(a[:, None, 2], b[None, :, 2]); iy2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(area_a[:, None] + area_b[None, :] - inter, 1e-9)


def tracking_metrics(gt_mot_txt, pred_mot_txt, iou_threshold=0.5):
    """Both files in MOTChallenge format (the pipeline writes tracks_mot.txt in it; CVAT exports 'MOT 1.1')."""
    G, P = load_mot(gt_mot_txt, is_gt=True), load_mot(pred_mot_txt)
    tp = fp = fn = switches = n_gt = n_pred = 0
    last = {}                    # gt id -> pred id it was last matched to
    overlap = Counter()          # (gt id, pred id) -> frames with IoU >= threshold, for IDF1
    for f in sorted(set(G) | set(P)):
        g, p = G.get(f, []), P.get(f, [])
        n_gt += len(g); n_pred += len(p)
        if not g or not p:
            fp += len(p); fn += len(g)
            continue
        iou = iou_matrix([b for _, b in g], [b for _, b in p])
        for gi, pi in zip(*np.nonzero(iou >= iou_threshold)):
            overlap[(g[gi][0], p[pi][0])] += 1
        matches, used_g, used_p = [], set(), set()
        for gi, (gid, _) in enumerate(g):            # keep last frame's correspondences while they still overlap
            for pi, (pid, _) in enumerate(p):
                if last.get(gid) == pid and pi not in used_p and iou[gi, pi] >= iou_threshold:
                    matches.append((gi, pi)); used_g.add(gi); used_p.add(pi)
                    break
        rg = [i for i in range(len(g)) if i not in used_g]
        rp = [j for j in range(len(p)) if j not in used_p]
        if rg and rp:
            cost = 1.0 - iou[np.ix_(rg, rp)]
            cost[cost > 1.0 - iou_threshold] = 1e6
            for r, c in zip(*linear_sum_assignment(cost)):
                if cost[r, c] < 1e6:
                    matches.append((rg[r], rp[c]))
        for gi, pi in matches:
            gid, pid = g[gi][0], p[pi][0]
            if gid in last and last[gid] != pid:
                switches += 1
            last[gid] = pid
        tp += len(matches); fp += len(p) - len(matches); fn += len(g) - len(matches)

    idtp = 0
    if overlap:
        gids = sorted({k[0] for k in overlap}); pids = sorted({k[1] for k in overlap})
        m = np.zeros((len(gids), len(pids)))
        for (gid, pid), n in overlap.items():
            m[gids.index(gid), pids.index(pid)] = n
        r, c = linear_sum_assignment(-m)
        idtp = int(m[r, c].sum())
    return {"MOTA": 100.0 * (1.0 - (fn + fp + switches) / n_gt) if n_gt else float("nan"),
            "IDF1": 100.0 * 2 * idtp / (n_gt + n_pred) if n_gt + n_pred else float("nan"),
            "ID_switches": switches,
            "det_precision": tp / (tp + fp) if tp + fp else 0.0,
            "det_recall": tp / n_gt if n_gt else 0.0}


def load_gt_events(path):
    """CSV with columns: type,start_s,end_s  (type = zone_entry | loitering), times relative to the clip start."""
    with open(path, newline="", encoding="utf-8") as f:
        return [{"type": r["type"].strip(), "start": float(r["start_s"]), "end": float(r["end_s"])} for r in csv.DictReader(f)]


def event_metrics(pred_events, gt_events, kind, tolerance_s=5.0):
    """A predicted event is correct when it falls inside an unmatched ground-truth event of the same type (± tolerance)."""
    preds = sorted(e["t"] for e in pred_events if e["type"] == kind)
    gts = [g for g in gt_events if g["type"] == kind]
    used = [False] * len(gts)
    tp = 0
    for t in preds:
        for i, g in enumerate(gts):
            if not used[i] and g["start"] - tolerance_s <= t <= g["end"] + tolerance_s:
                used[i] = True
                tp += 1
                break
    fp, fn = len(preds) - tp, len(gts) - tp
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"event": kind, "precision": p, "recall": r, "tp": tp, "fp": fp, "fn": fn}
