import datetime
import asyncio, json, os, websockets
import time
from redis_writer import write_to_redis, cleanup_old_data
import logging

PAIR = os.getenv("PAIR", "BTC-USDT")
WS_SYMBOL = PAIR.lower().replace("-", "")
WS_URL = f"wss://stream.binance.com:9443/ws/{WS_SYMBOL}@kline_1s"
REDIS_KEY = f"{PAIR}:live"
INTERVAL = 1.0

# Configuration du logging (au début du fichier)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


async def listen():
    logging.info("[%s] Connecting to: %s", PAIR, WS_URL)
    last_cleanup = time.time()
    CLEANUP_INTERVAL = 30 * 60  # 30 minutes en secondes

    while True:  # Retry loop
        try:
            async with websockets.connect(
                WS_URL, ping_interval=180, ping_timeout=600
            ) as ws:
                while True:
                    try:
                        msg = await ws.recv()
                        payload = json.loads(msg)
                        kline = payload["k"]

                        row = {
                            "timestamp": kline["t"],
                            "price": float(kline["c"]),
                            "volume": float(kline["v"]),
                            "open": float(kline["o"]),
                            "high": float(kline["h"]),
                            "low": float(kline["l"]),
                            "close": float(kline["c"]),
                        }

                        write_to_redis(REDIS_KEY, row)
                        if time.time() - last_cleanup > CLEANUP_INTERVAL:
                            cleanup_old_data(REDIS_KEY)
                            last_cleanup = time.time()

                    except websockets.ConnectionClosed as e:
                        logging.warning(
                            f"[{PAIR}] Connection closed: {e.code} - {e.reason}"
                        )
                        break  # Exit inner loop to reconnect

                    except Exception as e:
                        logging.error(f"[{PAIR}] WebSocket error: {e}")
                        await asyncio.sleep(5)

        except Exception as e:
            logging.error(f"[{PAIR}] Failed to connect: {e}")
            await asyncio.sleep(10)  # Wait before retrying


if __name__ == "__main__":
    asyncio.run(listen())
