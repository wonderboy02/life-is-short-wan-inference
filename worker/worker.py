"""
Wan Worker - Main polling loop for task processing
"""
import os
import sys
import time
import signal
import threading
import yaml
from pathlib import Path
from typing import Dict, Any

# Add worker directory to path
sys.path.insert(0, str(Path(__file__).parent))

from logger import setup_logger, log_task_start, log_task_complete, log_step, log_error
from api_client import VercelAPIClient
from storage import download_file, upload_file, cleanup_file, get_content_type
from inference import WanInference
# from preprocess import preprocess_image  # 전처리 미사용 시 주석처리


class WanWorker:
    """Main worker class for polling and processing tasks"""

    def __init__(self, config_path: str = "worker/config.yaml"):
        """
        Initialize worker

        Args:
            config_path: Path to config.yaml file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Setup logger
        self.logger = setup_logger(
            log_dir=self.config["log_dir"],
            worker_id=self.config["worker_id"]
        )

        # Initialize API client
        self.api_client = VercelAPIClient(
            base_url=self.config["vercel_api_url"],
            worker_token=self.config["worker_token"],
            worker_id=self.config["worker_id"],
            timeout=self.config["api_timeout"]
        )

        # Initialize inference engine
        inference_config = {
            "task_type": self.config["task_type"],
            "video_size": self.config["video_size"],
            "frame_num": self.config["frame_num"],
            "sample_solver": self.config["sample_solver"],
            "sample_steps": self.config["sample_steps"],
            "cfg_scale": self.config["cfg_scale"]
        }

        self.inference = WanInference(
            wan_repo_path=self.config["wan_repo_path"],
            model_path=self.config["model_path"],
            config=inference_config
        )

        # Setup temp directory
        Path(self.config["temp_dir"]).mkdir(parents=True, exist_ok=True)

        # Shutdown flag
        self.shutdown_requested = False

        # Heartbeat control
        self.heartbeat_active = False
        self.heartbeat_interval = self.config.get("heartbeat_interval", 120)  # 2 minutes

        self.logger.info("="*60)
        self.logger.info(f"Worker initialized: {self.config['worker_id']}")
        self.logger.info(f"Vercel API: {self.config['vercel_api_url']}")
        self.logger.info(f"Model path: {self.config['model_path']}")
        self.logger.info("="*60)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        self.logger.info("Shutdown signal received, finishing current task...")
        self.shutdown_requested = True

    def _heartbeat_loop(self, item_id: str):
        """Background heartbeat loop to extend task lease"""
        while self.heartbeat_active:
            time.sleep(self.heartbeat_interval)
            if not self.heartbeat_active:
                break
            try:
                success = self.api_client.heartbeat(item_id, extend_seconds=300)
                if success:
                    self.logger.info(f"[HEARTBEAT] Lease extended for item {item_id}")
            except Exception as e:
                self.logger.warning(f"[HEARTBEAT] Failed: {e}")

    def process_task(self, task: Dict[str, Any]) -> bool:
        """
        Process a single task

        Args:
            task: Task dictionary from API

        Returns:
            True if task completed successfully, False otherwise
        """
        item_id = task["item_id"]
        group_id = task.get("group_id", "unknown")
        photo_storage_path = task["photo_storage_path"]
        prompt = task.get("prompt")
        frame_num = task.get("frame_num")  # Optional: frame number override from API

        log_task_start(self.logger, item_id, group_id)

        # Define temp file paths
        input_filename = Path(photo_storage_path).name
        temp_input = Path(self.config["temp_dir"]) / f"{item_id}_input{Path(input_filename).suffix}"
        temp_output = Path(self.config["temp_dir"]) / f"{item_id}_output.mp4"

        # Start heartbeat thread
        self.heartbeat_active = True
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(item_id,))
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        try:
            # Step 1: Get presigned download URL
            log_step(self.logger, 1, "Getting download URL...")
            presign_data = self.api_client.get_presigned_download_url(photo_storage_path)
            download_url = presign_data["url"]

            # Step 2: Download input image
            log_step(self.logger, 2, f"Downloading input image: {input_filename}")
            download_file(download_url, str(temp_input))
            self.logger.info(f"Downloaded to: {temp_input}")

            # # Step 2.5: Preprocess image (resize + pad to supported size)
            # log_step(self.logger, "2.5", "Preprocessing image...")
            # processed_path, video_size = preprocess_image(str(temp_input))
            # self.logger.info(f"Preprocessed to size: {video_size}")

            # Step 3: Run inference
            log_step(self.logger, 3, "Running Wan2.2 inference...")
            self.logger.info(f"Prompt: {prompt if prompt else '(default)'}")
            self.logger.info(f"Frame num: {frame_num if frame_num else '(default: 121)'}")
            self.inference.run(
                input_image_path=str(temp_input),
                output_video_path=str(temp_output),
                prompt=prompt,
                frame_num=frame_num  # Pass frame_num from API (None = use default 121)
            )
            self.logger.info(f"Inference complete: {temp_output}")

            # Step 4: Get presigned upload URL
            log_step(self.logger, 4, "Getting upload URL...")
            presign_data = self.api_client.get_presigned_upload_url(
                video_item_id=item_id,
                file_extension="mp4"
            )
            upload_url = presign_data["url"]
            video_storage_path = presign_data["storage_path"]

            # Step 5: Upload result
            log_step(self.logger, 5, "Uploading result video...")
            upload_file(str(temp_output), upload_url, "video/mp4")
            self.logger.info(f"Uploaded to: {video_storage_path}")

            # Step 6: Report success
            log_step(self.logger, 6, "Reporting task completion...")
            self.api_client.report_task_result(
                item_id=item_id,
                status="completed",
                video_storage_path=video_storage_path
            )

            log_task_complete(self.logger, item_id, "SUCCESS")

            # Cleanup temp files
            if self.config.get("auto_cleanup_temp", True):
                cleanup_file(str(temp_input))
                cleanup_file(str(temp_output))

            return True

        except Exception as e:
            # Report failure
            log_error(self.logger, f"Task {item_id} failed", e)

            try:
                self.api_client.report_task_result(
                    item_id=item_id,
                    status="failed",
                    error_message=str(e)
                )
            except Exception as report_error:
                log_error(self.logger, "Failed to report task failure", report_error)

            log_task_complete(self.logger, item_id, "FAILED")

            # Cleanup temp files
            cleanup_file(str(temp_input))
            cleanup_file(str(temp_output))

            return False

        finally:
            # Stop heartbeat thread
            self.heartbeat_active = False
            heartbeat_thread.join(timeout=1)

    def run(self):
        """Main polling loop"""
        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        self.logger.info("Starting polling loop...")
        self.logger.info(f"Polling interval: {self.config['polling_interval']} seconds")
        self.logger.info("")

        while not self.shutdown_requested:
            try:
                # Get next task
                self.logger.info("[POLLING] Requesting next task...")
                task = self.api_client.get_next_task(
                    lease_duration_seconds=self.config.get("lease_duration_seconds", 600)
                )

                if task is None:
                    self.logger.info("[IDLE] No task available")
                    self.logger.info(f"Waiting {self.config['polling_interval']} seconds...")
                    self.logger.info("")
                    time.sleep(self.config["polling_interval"])
                    continue

                # Process task
                self.logger.info(f"[TASK RECEIVED] item_id: {task['item_id']}")
                self.logger.info("")
                success = self.process_task(task)

                # Brief pause before next poll
                time.sleep(1)

            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt received, shutting down...")
                break

            except Exception as e:
                log_error(self.logger, "Error in main loop", e)
                self.logger.info(f"Retrying in {self.config['polling_interval']} seconds...")
                time.sleep(self.config["polling_interval"])

        self.logger.info("Worker shutdown complete")


def main():
    """Entry point"""
    # Get config path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else "worker/config.yaml"

    # Create and run worker
    worker = WanWorker(config_path)
    worker.run()


if __name__ == "__main__":
    main()
