"""One-off: send a real message to Mailpit to eyeball it. Not a pytest file."""

import asyncio

from app.domain.departments import Department
from app.services.mailer import send_to_department


async def main() -> None:
    await send_to_department(
        department=Department.KADRY,
        subject="Wniosek urlopowy",
        body="Chcialbym zglosic urlop na jutro.",
        sender_email="jan.kowalski@example.com",
    )
    print("Wyslano.")


asyncio.run(main())
