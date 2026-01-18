import time


def process_email(email: str) -> str:
    """
    Menja {timestamp} placeholder sa trenutnim vremenom u milisekundama.
    """
    if not email:  # Ovo menja email == null || email.isEmpty()
        return email

    if "{timestamp}" in email:
        # time.time() daje sekunde, množenje sa 1000 daje milisekunde (kao Java)
        timestamp = str(int(time.time() * 1000))
        return email.replace("{timestamp}", timestamp)

    return email