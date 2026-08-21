import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quant-radar")


async def main() -> None:
    logger.info("Quant Radar starting...")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
