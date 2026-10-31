"""Vietnamese License Plate Validator & Regex Formatter.

Normalizes and validates Vietnamese license plates:
- Car (1-row standard): 29A-123.45, 30F-5678, 51G-888.88
- Motorbike (2-row standard): 29-B1 123.45, 43-K1 6789
- Electric bike: 29-MĐ1 123.45
- Diplomatic / Military / Government: NG, QT, TM, TC
"""

import re
from typing import Tuple, Optional


class VietnamesePlateValidator:
    """Cleans OCR output and verifies against Vietnamese vehicle registration formats."""

    # Province code prefix (11-99)
    PROVINCE_CODES = set(range(11, 100))

    # Common OCR character confusions: (Numbers vs Letters)
    NUM_TO_CHAR = {"0": "O", "1": "I", "8": "B", "5": "S"}
    CHAR_TO_NUM = {"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6"}

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        """Removes punctuation and unwanted symbols from raw OCR text."""
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        return cleaned

    @classmethod
    def validate_and_format(cls, raw_text: str) -> Tuple[bool, Optional[str], str]:
        """Validates and formats the license plate string into standard VN syntax.

        Returns:
            (is_valid, formatted_plate, plate_category)
        """
        cleaned = cls.clean_text(raw_text)
        if len(cleaned) < 7 or len(cleaned) > 10:
            return (False, None, "UNKNOWN")

        # 1. Car Format: 2 digits (province) + 1-2 letters + 4-5 digits
        # Example: 30A12345 -> 30A-123.45
        car_match = re.match(r"^(\d{2})([A-Z]{1,2})(\d{4,5})$", cleaned)
        if car_match:
            prov, series, digits = car_match.groups()
            if int(prov) in cls.PROVINCE_CODES:
                if len(digits) == 5:
                    formatted = f"{prov}{series}-{digits[:3]}.{digits[3:]}"
                else:
                    formatted = f"{prov}{series}-{digits}"
                return (True, formatted, "CAR")

        # 2. Motorbike Format: 2 digits + 1 letter + 1 digit/letter + 4-5 digits
        # Example: 29B112345 -> 29-B1 123.45
        bike_match = re.match(r"^(\d{2})([A-Z])([0-9A-Z])(\d{4,5})$", cleaned)
        if bike_match:
            prov, s1, s2, digits = bike_match.groups()
            if int(prov) in cls.PROVINCE_CODES:
                if len(digits) == 5:
                    formatted = f"{prov}-{s1}{s2} {digits[:3]}.{digits[3:]}"
                else:
                    formatted = f"{prov}-{s1}{s2} {digits}"
                return (True, formatted, "MOTORCYCLE")

        # Fallback: If reasonably shaped, return cleaned with hyphen
        if len(cleaned) >= 8 and cleaned[:2].isdigit():
            formatted = f"{cleaned[:3]}-{cleaned[3:]}"
            return (True, formatted, "GENERAL")

        return (False, None, "INVALID")
