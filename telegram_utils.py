from typing import Tuple

from telegram import PhotoSize

# Telegram always provides various sizes of single photos.
def get_largest_photo_size(photos: Tuple[PhotoSize]) -> PhotoSize:
    largest_photo = photos[0]
    for photo_data in photos:
        if largest_photo.file_size < photo_data.file_size:
            largest_photo = photo_data
    return largest_photo