from typing import Dict, List, Any

def derive_run_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derives comprehensive communication, recovery, and protocol metrics from stored events."""
    metrics = {
        "messages_sent": 0,
        "messages_delivered": 0,
        "messages_dropped": 0,
        "drops_by_reason": {"loss": 0, "partition": 0},
        "messages_duplicated": 0,
        "messages_reordered": 0,
        "acks_sent": 0,
        "acks_received": 0,
        "acks_unmatched": 0,
        "timeouts": 0,
        "retransmissions": 0,
        "retries_exhausted": 0,
        "duplicates_suppressed": 0,
        "stale_updates_rejected": 0,
        "sync_requests": 0,
        "sync_responses": 0,
        "sync_applied": 0,
        "recoordination_attempts": 0,
        "degraded_peers": 0,
        "invalid_rejected": 0,
        "recovery_latencies": [],
    }

    # Tracking messages that experienced drop or retry
    messages_needing_recovery = set()
    messages_recovered = set()

    for ev in events:
        ev_type = ev.get("type", "")
        payload = ev.get("payload", {})
        msg_id = ev.get("msg_id")

        if ev_type == "SEND":
            metrics["messages_sent"] += 1
            if payload.get("kind") == "ACK":
                metrics["acks_sent"] += 1
        elif ev_type == "DELIVER":
            metrics["messages_delivered"] += 1
        elif ev_type == "DROP":
            metrics["messages_dropped"] += 1
            reason = payload.get("reason", "loss")
            metrics["drops_by_reason"][reason] = metrics["drops_by_reason"].get(reason, 0) + 1
            if msg_id:
                messages_needing_recovery.add(msg_id)
        elif ev_type == "DUPLICATE":
            metrics["messages_duplicated"] += 1
        elif ev_type == "REORDER":
            metrics["messages_reordered"] += 1
        elif ev_type == "TIMEOUT":
            metrics["timeouts"] += 1
            if msg_id:
                messages_needing_recovery.add(msg_id)
        elif ev_type == "RETRY":
            metrics["retransmissions"] += 1
            if msg_id:
                messages_needing_recovery.add(msg_id)
        elif ev_type == "RETRY_EXHAUSTED":
            metrics["retries_exhausted"] += 1
        elif ev_type == "ACK_RECEIVED":
            metrics["acks_received"] += 1
            rec_lat = payload.get("recovery_latency")
            if rec_lat is not None:
                metrics["recovery_latencies"].append(float(rec_lat))
            if msg_id and msg_id in messages_needing_recovery:
                messages_recovered.add(msg_id)
        elif ev_type == "ACK_UNMATCHED":
            metrics["acks_unmatched"] += 1
        elif ev_type == "DUP_SUPPRESSED":
            metrics["duplicates_suppressed"] += 1
        elif ev_type == "STALE_REJECTED":
            metrics["stale_updates_rejected"] += 1
        elif ev_type == "SYNC_REQ":
            metrics["sync_requests"] += 1
        elif ev_type == "SYNC_RESP":
            metrics["sync_responses"] += 1
        elif ev_type == "SYNC_APPLIED":
            metrics["sync_applied"] += 1
        elif ev_type == "RECOORD_ATTEMPT":
            metrics["recoordination_attempts"] += 1
        elif ev_type == "DEGRADED_PEER":
            metrics["degraded_peers"] += 1
        elif ev_type == "INVALID_REJECTED":
            metrics["invalid_rejected"] += 1

    total_needing = len(messages_needing_recovery)
    total_recovered = len(messages_recovered)
    rec_latencies = metrics.pop("recovery_latencies")

    metrics["messages_needing_recovery"] = total_needing
    metrics["messages_recovered"] = total_recovered
    metrics["recovery_success_rate"] = (total_recovered / total_needing) if total_needing > 0 else 1.0
    metrics["mean_recovery_latency"] = (sum(rec_latencies) / len(rec_latencies)) if rec_latencies else 0.0

    return metrics
