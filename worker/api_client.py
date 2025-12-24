"""
Vercel API Client for Wan Worker
"""
import requests
import time
from typing import Optional, Dict, Any


class VercelAPIClient:
    """Client for communicating with Vercel backend API"""

    def __init__(self, base_url: str, worker_token: str, worker_id: str, timeout: int = 30):
        """
        Initialize API client

        Args:
            base_url: Vercel API base URL (e.g., https://your-app.vercel.app/api)
            worker_token: Authentication token for worker
            worker_id: Unique worker identifier
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.worker_token = worker_token
        self.worker_id = worker_id
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Worker {worker_token}',
            'Content-Type': 'application/json'
        })

    def get_next_task(self, lease_duration_seconds: int = 600) -> Optional[Dict[str, Any]]:
        """
        Request next available task from the queue

        Args:
            lease_duration_seconds: How long to lease the task (default: 600 seconds)

        Returns:
            Task dict with keys: item_id, group_id, photo_id, prompt, photo_storage_path, leased_until
            None if no task available
        """
        url = f"{self.base_url}/worker/next-task"
        payload = {
            "worker_id": self.worker_id,
            "lease_duration_seconds": lease_duration_seconds
        }

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()

            # No task available
            if not result.get('success') or result.get('data') is None:
                return None

            return result['data']

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get next task: {str(e)}")

    def get_presigned_download_url(self, storage_path: str) -> Dict[str, Any]:
        """
        Get presigned URL for downloading input image

        Args:
            storage_path: Storage path of the input image (e.g., "group-id/photo-id_original.png")

        Returns:
            Dict with keys: url, expires_in
        """
        url = f"{self.base_url}/worker/presign"
        payload = {
            "operation": "download",
            "storage_path": storage_path
        }

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result['data']

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get presigned download URL: {str(e)}")

    def get_presigned_upload_url(self, video_item_id: str, file_extension: str = "mp4") -> Dict[str, Any]:
        """
        Get presigned URL for uploading result video

        Args:
            video_item_id: Video item ID (same as item_id)
            file_extension: File extension (default: "mp4")

        Returns:
            Dict with keys: url, expires_in, storage_path
        """
        url = f"{self.base_url}/worker/presign"
        payload = {
            "operation": "upload",
            "video_item_id": video_item_id,
            "file_extension": file_extension
        }

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result['data']

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get presigned upload URL: {str(e)}")

    def report_task_result(self, item_id: str, status: str,
                          video_storage_path: str = None, error_message: str = None,
                          veo_operation_id: str = None) -> bool:
        """
        Report task completion result

        Args:
            item_id: Item ID (video_item_id)
            status: "completed" or "failed"
            video_storage_path: Storage path for output video (required for completed)
            error_message: Error message (required for failed)
            veo_operation_id: Optional tracking ID

        Returns:
            True if report successful
        """
        url = f"{self.base_url}/worker/report"
        payload = {
            "item_id": item_id,
            "worker_id": self.worker_id,
            "status": status
        }

        if status == "completed":
            if not video_storage_path:
                raise ValueError("video_storage_path required for status=completed")
            payload["video_storage_path"] = video_storage_path
            if veo_operation_id:
                payload["veo_operation_id"] = veo_operation_id
        elif status == "failed":
            if not error_message:
                raise ValueError("error_message required for status=failed")
            payload["error_message"] = error_message

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to report task result: {str(e)}")

    def heartbeat(self, item_id: str, extend_seconds: int = 300) -> bool:
        """
        Send heartbeat to extend task lease

        Args:
            item_id: Item ID (video_item_id)
            extend_seconds: Seconds to extend lease by (default: 300)

        Returns:
            True if heartbeat successful
        """
        url = f"{self.base_url}/worker/heartbeat"
        payload = {
            "item_id": item_id,
            "worker_id": self.worker_id,
            "extend_seconds": extend_seconds
        }

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            # Heartbeat is optional, don't raise exception
            return False
