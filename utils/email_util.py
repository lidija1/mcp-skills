import time


def process_email(email: str) -> str:
    """
    Replaces the placeholder "{timestamp}" in the email string with the current timestamp in milliseconds.
    """
    if not email:  # This changes email == null || email.isEmpty()
        return email

    if "{timestamp}" in email:
        # time.time() gives seconds, multiply by 1000 for milliseconds
        timestamp = str(int(time.time() * 1000))
        return email.replace("{timestamp}", timestamp)

    return email