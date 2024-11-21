import base64
import os
from io import BytesIO
from fastapi import UploadFile, HTTPException, status
import aiofiles

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
    
    
async def read_and_validate_image(file: UploadFile) -> bytes:
    # Validate the image content-type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid image type: {file.filename}"
        )

    # Read the file content asynchronously
    content = await file.read()

    # Check file size (limit to 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {file.filename}",
        )
    return content