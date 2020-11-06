"""
file_cache_manager.py - Manage a local cache of files synchronized through S3

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
from util.logger import get_logger


load_dotenv()


class FileCacheManager(object):
    """
    Compares the update time on S3 to the local file's update time.
    If the S3 file is newer or the local file does not exist, downloads
    the latest file to the local cache folder then returns the path
    of the locally cached file.
    """
    def __init__(self, s3_path: str = None, local_path: str = None):
        self.logger = get_logger('fcm')
        if not s3_path:
            self.s3_path = os.environ['DOCX_S3_PATH']
        else:
            self.s3_path = s3_path

        if not local_path:
            self.local_path = os.environ['DOCX_PATH']
        else:
            self.local_path = local_path

    def get_filename(self, filename: str) -> str:
        """
        Gets the full path name of the requested file.
        First checks to see if the local file exists. If not, then
        sees if the file exists in the S3 bucket. If not, returns None.
        If so, downloads the file from S3, saves it to the local_path,
        and returns the full file path of the requested file.

        If the file does exist locally, compares the update date/time of
        the local file to the corresponding object in S3. If the S3 object
        is newer, the S3 object is downloaded and cached.

        Args:
            filename (str): The name of the file to be retrieved
        Returns:
            (str): The absolute path of the file or None if not found.
        """
        s3 = _connect()
        self.logger.debug("Searching S3 bucket '%s' for key '%s'", self.s3_path, filename)
        s3_modified_date = _s3_modified_date(s3, self.s3_path, filename)
        self.logger.debug("S3 modified: %s", s3_modified_date)
        local_modified_date = _local_modified_date(self.local_path, filename)
        self.logger.debug("Local modified: %s", local_modified_date)
        local_filename = os.path.join(self.local_path, filename)
        self.logger.debug("Local filename: %s", local_filename)

        # See if file exists anywhere
        if not s3_modified_date and not local_modified_date:
            self.logger.error("Template %s not found locally or on S3.", filename)
            return None

        # See if our file is newer than the S3 file
        if local_modified_date >= s3_modified_date:
            self.logger.debug("Local file is newer than S3")
            return local_filename

        # S3 file is newer . . . download it.
        self.logger.debug("S3 file is newer than local file")
        config = TransferConfig(use_threads=False)
        s3.Object(self.s3_path, filename).download_file(local_filename, Config=config)
        self.logger.debug("%s downloaded from S3", local_filename)
        return local_filename

    def synchronize_file(self, filename: str) -> bool:
        """
        Copy a local file to the remote S3 service so that other
        nodes can pick it up.
        """
        s3 = _connect()
        local_filename = os.path.join(self.local_path, filename)
        s3.Bucket(self.s3_path).upload_file(local_filename, filename)


def _connect():
    """
    Connects to the S3 service and returns a Boto3 object.
    """
    return boto3.resource('s3')


def _s3_modified_date(s3_client, bucket, filename) -> float:
    try:
        return s3_client.Bucket(bucket).Object(filename).last_modified.timestamp()
    except ClientError:
        pass

    return 0.0


def _local_modified_date(local_path, filename) -> float:
    try:
        local_filename = os.path.join(local_path, filename)
        return os.path.getmtime(local_filename)
    except FileNotFoundError:
        pass

    return 0.0
