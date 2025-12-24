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
            'Authorization': f'Bearer {worker_token}',
            'Content-Type': 'application/json'
        })

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Request next available task from the queue

        Returns:
            Task dict with keys: task_id, job_id, input_path, params
            None if no task available
        """
        url = f"{self.base_url}/worker/next-task"
        payload = {"worker_id": self.worker_id}

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # No task available
            if data.get('task') is None:
                return None

            return data['task']

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get next task: {str(e)}")

    def get_presigned_url(self, task_id: str, url_type: str,
                          filename: str = None, content_type: str = None) -> Dict[str, Any]:
        """
        Get presigned URL for download or upload

        Args:
            task_id: Task ID
            url_type: "download_input" or "upload_output"
            filename: Filename for upload (required for upload_output)
            content_type: MIME type for upload (required for upload_output)

        Returns:
            Dict with keys: url, expires_at, (output_path for upload)
        """
        url = f"{self.base_url}/worker/presign"
        payload = {
            "task_id": task_id,
            "type": url_type
        }

        if url_type == "upload_output":
            if not filename or not content_type:
                raise ValueError("filename and content_type required for upload_output")
            payload["filename"] = filename
            payload["content_type"] = content_type

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get presigned URL: {str(e)}")

    def report_task_result(self, task_id: str, status: str,
                          output_path: str = None, error: str = None) -> bool:
        """
        Report task completion result

        Args:
            task_id: Task ID
            status: "done" or "failed"
            output_path: Storage path for output (required for done)
            error: Error message (required for failed)

        Returns:
            True if report successful
        """
        url = f"{self.base_url}/worker/report"
        payload = {
            "task_id": task_id,
            "status": status
        }

        if status == "done":
            if not output_path:
                raise ValueError("output_path required for status=done")
            payload["output_path"] = output_path
        elif status == "failed":
            if not error:
                raise ValueError("error message required for status=failed")
            payload["error"] = error

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to report task result: {str(e)}")

    def heartbeat(self, task_id: str, extend_seconds: int = 600) -> bool:
        """
        Send heartbeat to extend task lease (optional feature)

        Args:
            task_id: Task ID
            extend_seconds: Seconds to extend lease by

        Returns:
            True if heartbeat successful
        """
        url = f"{self.base_url}/worker/heartbeat"
        payload = {
            "task_id": task_id,
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
