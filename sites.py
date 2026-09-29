import re


def detect_site(raw):
    """Map a receipt code to (site, normalized_code), or None if unrecognized.

    Tim Hortons (telltims.ca) codes are 21 digits; Dairy Queen (mydqexperience.com)
    codes are 15 letters/digits. Dashes and spaces are ignored.
    """
    code = re.sub(r'[\s-]', '', raw or '').upper().replace('O', '0')  # DQ receipts never use the letter O
    if re.fullmatch(r'\d{21}', code):
        return 'tims', code
    if re.fullmatch(r'[A-Z0-9]{15}', code):
        return 'dq', code
    return None
