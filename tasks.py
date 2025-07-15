from celery_app import celery_app
from networks.ethereum import check_ethereum_transaction  # твой файл с async-функцией
import asyncio
from config import ETHERSCAN_API_KEY, ERC20_CONFIRMATIONS, logger
# from utils.google_sheets import write_to_google_sheets

@celery_app.task(bind=True, max_retries=30)
def check_erc20_transaction_task(self, tx_hash, target_address):
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    result = loop.run_until_complete(check_ethereum_transaction(tx_hash, target_address))
    logger.info("redis -------------------- result: %s", result)
    logger.info("ETH ---------------------------------------------------------------: %s", result)
    if not result["success"]:
        # Недостаточно подтверждений → retry
        if "подтверждений" in result["error"]:
            raise self.retry(countdown=20)
        else:
            # Фатальная ошибка (не тот адрес, битая транзакция) → завершить
            return
    return result