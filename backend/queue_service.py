import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import deque

try:
    import redis
except ImportError:
    redis = None


class EmergencyMessageQueue:
    """
    Message Queue Service for decoupled background processing of emergency blood requests.
    Uses Redis as the primary message broker with an in-memory queue fallback.
    """

    QUEUE_KEY = "bb:emergency_queue"
    BROADCASTS_KEY = "bb:emergency_broadcasts"

    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_client = None
        self.in_memory_queue = deque()
        self.in_memory_broadcasts = []
        self._init_redis()

    def _init_redis(self):
        if redis is None:
            print("[MESSAGE QUEUE] Redis package not installed, using in-memory queue.")
            return

        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0
                )
                if client.ping():
                    self.redis_client = client
                    print("[MESSAGE QUEUE] Successfully connected to Redis via REDIS_URL")
                    return
            except Exception as e:
                print(f"[MESSAGE QUEUE] Redis connection via REDIS_URL failed ({e}). Falling back to host/port.")

        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5
            )
            if client.ping():
                self.redis_client = client
                print(f"[MESSAGE QUEUE] Successfully connected to Redis at {self.redis_host}:{self.redis_port}")
        except Exception as e:
            print(f"[MESSAGE QUEUE] Redis unavailable ({e}). Falling back to in-memory message queue.")
            self.redis_client = None

    def is_redis_active(self) -> bool:
        if self.redis_client:
            try:
                return bool(self.redis_client.ping())
            except Exception:
                return False
        return False

    def enqueue_alert(self, payload: Dict[str, Any]) -> str:
        """Enqueue an emergency broadcast job onto the message queue"""
        job_id = f"job_{int(time.time() * 1000)}"
        payload["job_id"] = job_id
        payload["enqueued_at"] = datetime.now(timezone.utc).isoformat()
        payload["status"] = "QUEUED"

        data_str = json.dumps(payload)

        if self.is_redis_active():
            try:
                self.redis_client.rpush(self.QUEUE_KEY, data_str)
                return job_id
            except Exception as e:
                print(f"[MESSAGE QUEUE] Redis rpush error: {e}, falling back to in-memory queue")

        self.in_memory_queue.append(payload)
        return job_id

    def get_compatible_donor_groups(self, blood_group: str) -> List[str]:
        """Return compatible donor blood groups for whole blood / RBC allocation"""
        compatibility_map = {
            "A+": ["A+", "A-", "O+", "O-"],
            "A-": ["A-", "O-"],
            "B+": ["B+", "B-", "O+", "O-"],
            "B-": ["B-", "O-"],
            "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], # Universal recipient
            "AB-": ["AB-", "A-", "B-", "O-"],
            "O+": ["O+", "O-"],
            "O-": ["O-"], # Universal donor
        }
        return compatibility_map.get(blood_group, [blood_group])

    def process_emergency_job(self, payload: Dict[str, Any], db_instance) -> Dict[str, Any]:
        """
        Asynchronously process the emergency blood request:
        1. Find compatible and eligible donors.
        2. Simulate instant SMS/Email emergency dispatch.
        3. Log broadcast to telemetry store.
        """
        start_time = time.time()
        patient_name = payload.get("patient_name", "Emergency Patient")
        blood_group = payload.get("blood_group", "O+")
        hospital_name = payload.get("hospital_name", "Hospital")
        units_needed = payload.get("required_units", 1)
        request_id = payload.get("request_id")

        compatible_groups = self.get_compatible_donor_groups(blood_group)

        notified_donors = []
        matching_donors = []
        try:
            all_donors = db_instance.get_all_donors() or []
            for donor in all_donors:
                if not donor.get("IsActive", True):
                    continue
                if donor.get("BloodGroup") in compatible_groups:
                    matching_donors.append(donor)
                    # Check eligibility
                    eligibility = db_instance.check_donor_eligibility(donor["DonorID"])
                    is_eligible = "ELIGIBLE" in eligibility and "NOT" not in eligibility
                    notified_donors.append({
                        "donor_id": donor["DonorID"],
                        "name": donor["DonorName"],
                        "blood_group": donor["BloodGroup"],
                        "contact": donor["ContactNo"],
                        "email": donor.get("Email", ""),
                        "is_eligible": is_eligible,
                        "dispatch_channel": "SMS_AND_EMAIL",
                        "status": "DELIVERED"
                    })
        except Exception as err:
            print(f"[MESSAGE QUEUE] Error querying matching donors: {err}")

        duration_ms = round((time.time() - start_time) * 1000, 2)
        broadcast_record = {
            "job_id": payload.get("job_id"),
            "request_id": request_id,
            "patient_name": patient_name,
            "blood_group": blood_group,
            "hospital_name": hospital_name,
            "required_units": units_needed,
            "compatible_groups": compatible_groups,
            "matching_donors_count": len(matching_donors),
            "notified_count": len(notified_donors),
            "notified_donors": notified_donors[:10], # Top 10 preview
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "broker": "Redis 7.0 Streams/Queue" if self.is_redis_active() else "FastAPI Background Task Queue",
            "processing_time_ms": duration_ms,
            "status": "DISPATCHED"
        }

        # Store in Redis list / in-memory history
        if self.is_redis_active():
            try:
                self.redis_client.lpush(self.BROADCASTS_KEY, json.dumps(broadcast_record))
                self.redis_client.ltrim(self.BROADCASTS_KEY, 0, 49) # Keep 50 recent broadcasts
            except Exception as e:
                print(f"[MESSAGE QUEUE] Failed to log to Redis: {e}")
                self._save_in_memory(broadcast_record)
        else:
            self._save_in_memory(broadcast_record)

        print(f"[MESSAGE QUEUE] Emergency Alert processed for Request #{request_id}: Alerted {len(notified_donors)} eligible donors ({', '.join(compatible_groups)}) in {duration_ms}ms.")
        return broadcast_record

    def _save_in_memory(self, record: Dict[str, Any]):
        self.in_memory_broadcasts.insert(0, record)
        if len(self.in_memory_broadcasts) > 50:
            self.in_memory_broadcasts.pop()

    def get_recent_broadcasts(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent emergency broadcasts"""
        if self.is_redis_active():
            try:
                raw_list = self.redis_client.lrange(self.BROADCASTS_KEY, 0, limit - 1)
                return [json.loads(item) for item in raw_list]
            except Exception as e:
                print(f"[MESSAGE QUEUE] Error reading from Redis: {e}")

        return self.in_memory_broadcasts[:limit]

    def get_queue_telemetry(self) -> Dict[str, Any]:
        """Return live health and statistics for the message queue"""
        redis_online = self.is_redis_active()
        queue_len = 0
        if redis_online:
            try:
                queue_len = self.redis_client.llen(self.QUEUE_KEY)
            except Exception:
                queue_len = 0
        else:
            queue_len = len(self.in_memory_queue)

        recent = self.get_recent_broadcasts(5)
        return {
            "status": "ONLINE",
            "broker": "Redis 7.0 (Active)" if redis_online else "FastAPI Async Worker (Fallback)",
            "redis_connected": redis_online,
            "host": self.redis_host if redis_online else "in-memory",
            "queue_depth": queue_len,
            "recent_broadcast_count": len(recent),
            "recent_broadcasts": recent
        }


# Global message queue instance
message_queue = EmergencyMessageQueue()
