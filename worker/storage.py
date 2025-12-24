"""
Storage utilities for downloading and uploading files via presigned URLs
"""
import requests
from pathlib import Path
from typing import Optional


def download_file(presigned_url: str, save_path: str, chunk_size: int = 8192) -> str:
    """
    Download file from presigned URL

    Args:
        presigned_url: Presigned download URL from Vercel API
        save_path: Local path to save the downloaded file
        chunk_size: Download chunk size in bytes

    Returns:
        Path to downloaded file

    Raises:
        Exception if download fails
    """
    try:
        # Ensure parent directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Stream download
        response = requests.get(presigned_url, stream=True, timeout=300)
        response.raise_for_status()

        # Write to file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        return save_path

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download file: {str(e)}")
    except IOError as e:
        raise Exception(f"Failed to save file: {str(e)}")


def upload_file(file_path: str, presigned_url: str, content_type: str = "video/mp4") -> bool:
    """
    Upload file to presigned URL

    Args:
        file_path: Local file path to upload
        presigned_url: Presigned upload URL from Vercel API
        content_type: MIME type of the file

    Returns:
        True if upload successful

    Raises:
        Exception if upload fails
    """
    try:
        # Check file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file size for logging
        file_size = Path(file_path).stat().st_size

        # Upload file
        with open(file_path, 'rb') as f:
            response = requests.put(
                presigned_url,
                data=f,
                headers={'Content-Type': content_type},
                timeout=600  # 10 minutes for large files
            )
            response.raise_for_status()

        return True

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to upload file: {str(e)}")
    except IOError as e:
        raise Exception(f"Failed to read file: {str(e)}")


def cleanup_file(file_path: str) -> bool:
    """
    Delete temporary file

    Args:
        file_path: Path to file to delete

    Returns:
        True if deleted, False if file not found
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception:
        return False


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename

    Args:
        filename: Filename or path

    Returns:
        Extension including dot (e.g., ".png", ".mp4")
    """
    return Path(filename).suffix


def get_content_type(filename: str) -> str:
    """
    Determine MIME type from filename

    Args:
        filename: Filename or path

    Returns:
        MIME type string
    """
    extension = get_file_extension(filename).lower()

    content_types = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.webm': 'video/webm',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }

    return content_types.get(extension, 'application/octet-stream')
