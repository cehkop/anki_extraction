import base64
import os
from io import BytesIO
import imghdr
from fastapi import UploadFile, HTTPException, status
from pathlib import Path

# Function to convert an image file to base64 format
def image_to_base64(image):
    """
    Convert an image file or binary stream to a Base64 encoded string.
    :param image: File path (str) or BytesIO object
    :return: Base64 encoded string
    """
    if isinstance(image, (str, bytes, os.PathLike)):
        # If image is a file path
        with open(image, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    elif isinstance(image, BytesIO):
        # If image is a binary stream
        return base64.b64encode(image.read()).decode("utf-8")
    else:
        raise TypeError("Expected a file path or BytesIO object.")
    
    

# Helper function to validate and read uploaded image files
async def read_and_validate_image(file: UploadFile) -> bytes:
    filename = Path(file.filename).name  # Prevent directory traversal
    content = await file.read()
    # Check file size (limit to 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {filename}",
        )

    # Validate image type
    file_type = imghdr.what(None, h=content)
    if file_type not in ["jpeg", "png", "jpg", "webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type: {filename}",
        )

    return content