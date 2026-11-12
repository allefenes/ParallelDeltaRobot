"""`python -m delta_runner`: koşucu sunucusunu başlatır."""

import asyncio

from .server import main

asyncio.run(main())
