"""
Wan2.2 Inference Wrapper
"""
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any


class WanInference:
    """Wrapper for Wan2.2 generate.py"""

    def __init__(self, wan_repo_path: str, model_path: str, config: Dict[str, Any]):
        """
        Initialize inference wrapper

        Args:
            wan_repo_path: Path to Wan2.2 repository
            model_path: Path to model checkpoint directory
            config: Inference configuration dict
        """
        self.wan_repo_path = Path(wan_repo_path)
        self.model_path = Path(model_path)
        self.config = config

        # Validate paths
        if not self.wan_repo_path.exists():
            raise FileNotFoundError(f"Wan2.2 repo not found: {wan_repo_path}")
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        self.generate_script = self.wan_repo_path / "generate.py"
        if not self.generate_script.exists():
            raise FileNotFoundError(f"generate.py not found: {self.generate_script}")

    def run(self, input_image_path: str, output_video_path: str,
            prompt: str = None, video_size: str = None) -> str:
        """
        Run Wan2.2 inference

        Args:
            input_image_path: Path to input image
            output_video_path: Path where output video will be saved
            prompt: Text prompt (optional, will use default if not provided)
            video_size: Video size (e.g. "1280*704", optional, uses config default if not provided)

        Returns:
            Path to generated video file

        Raises:
            Exception if inference fails
        """
        # Validate input
        if not Path(input_image_path).exists():
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        # Ensure output directory exists
        Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)

        # Build command (--size removed: ti2v-5B follows input image aspect ratio)
        cmd = [
            "python",
            str(self.generate_script),
            "--task", self.config.get("task_type", "ti2v-5B"),
            "--ckpt_dir", str(self.model_path),
            "--image", input_image_path,
            "--save_file", output_video_path,
            # --size option removed: Wan2.2 automatically uses input image dimensions
            "--frame_num", str(self.config.get("frame_num", 81)),
            "--sample_solver", self.config.get("sample_solver", "unipc"),
            "--sample_steps", str(self.config.get("sample_steps", 30)),
            "--cfg_scale", str(self.config.get("cfg_scale", 5.0))
        ]

        # Add prompt if provided
        if prompt:
            cmd.extend(["--prompt", prompt])

        # Execute inference
        try:
            # Change to Wan2.2 directory for execution
            result = subprocess.run(
                cmd,
                cwd=str(self.wan_repo_path),
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise Exception(f"Inference failed with code {result.returncode}: {error_msg}")

            # Verify output file was created
            if not Path(output_video_path).exists():
                raise Exception(f"Output file was not created: {output_video_path}")

            return output_video_path

        except subprocess.TimeoutExpired:
            raise Exception("Inference timed out after 30 minutes")
        except Exception as e:
            raise Exception(f"Inference execution failed: {str(e)}")

    def validate_config(self) -> bool:
        """
        Validate inference configuration

        Returns:
            True if config is valid

        Raises:
            ValueError if config is invalid
        """
        required_keys = ["task_type", "video_size", "frame_num"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

        # Validate frame_num (must be 4n+1)
        frame_num = self.config["frame_num"]
        if (frame_num - 1) % 4 != 0:
            raise ValueError(f"frame_num must be 4n+1, got {frame_num}")

        return True
