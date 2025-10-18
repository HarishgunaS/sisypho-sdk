"""
Core library for interacting with the user.
"""

from typing import List, Union, Dict, Any
import logging

logger = logging.getLogger(__name__)

def present_files(alert_title: str, alert_message: str, files: List[str]) -> None:
    """
    Present a list of files to the user.

    Args:
        alert_title: The title of the alert.
        alert_message: The message of the alert.
        files: The list of files to present to the user.

    Returns:
        None

    Examples:
        >>> present_files(alert_title="Files", alert_message="Please select a file", files=["file1.txt", "file2.txt"])
    """
    print({"__type__": "present_files", "alert_title": alert_title, "alert_message": alert_message, "files": files})