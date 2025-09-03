import asyncio
import concurrent.futures
from threading import Thread
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo 

from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from handlers.crypto import CryptoFSM
import redis
from redis.asyncio import Redis as AsyncRedis
from config import REDIS_DB_FSM, REDIS_DB, REDIS_KEY_PREFIX_ERC, REDIS_KEY_PREFIX_TRC, REDIS_URL
# Conditional import for Celery
try:
    from celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None

# Fallback decorator when Celery is not available
def celery_task_fallback(func):
    """Fallback decorator when Celery is not available"""
    if CELERY_AVAILABLE:
        return celery_app.task(func)
    else:
        # Return the function as-is when Celery is disabled
        return func

from networks.ethereum import check_transaction_stages
from networks.tron import check_tron_transaction
from handlers.crypto import send_telegram_notification
from google_utils import save_transaction_hash, update_transaction_status
from config import logger

# --- Настройки ---

PENDING_TTL = 3 * 60 * 60                  # 3 часа TTL ключа
MAX_PENDING_DURATION = timedelta(minutes=2)  # в тексте так и было – 2 часа

r = redis.Redis.from_url(REDIS_URL, db=REDIS_DB, decode_responses=True)

# --- Async Redis Singleton ---
r_async: AsyncRedis | None = None

def get_async_redis() -> AsyncRedis:
    global r_async
    if r_async is None:
        r_async = AsyncRedis.from_url(REDIS_URL, db=REDIS_DB_FSM)
    return r_async

# async loop infra
_loop = None
_executor = None
_loop_thread = None

def get_or_create_event_loop():
    global _loop, _executor, _loop_thread
    if _loop is None:
        _loop = asyncio.new_event_loop()
        def run_loop():
            asyncio.set_event_loop(_loop)
            _loop.run_forever()
        _loop_thread = Thread(target=run_loop, daemon=True)
        _loop_thread.start()
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    return _loop

def run_async_coroutine(coro, timeout=40):
    loop = get_or_create_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)

def _redis_key(tx_hash: str) -> str:
    return f"{REDIS_KEY_PREFIX_ERC}{tx_hash}"

def _touch_ttl(key: str):
    if r:
        r.expire(key, PENDING_TTL)

def _store_initial(username, chat_id, bot_id, tx_hash, target_address, lang, amount, network):
    if not r:
        logger.error("Redis недоступен")
        return
    
    key = _redis_key(tx_hash)
    now = datetime.now(timezone.utc).isoformat()
    r.hset(key, mapping={
        "username": username,
        "chat_id": int(chat_id),
        "bot_id": int(bot_id),
        "target_address": target_address,
        "first_seen": now,
        "lang": lang,
        "stage": "in_block,is_erc20,recipient,transfer_params,confirmations",
        "last_error_code": "",
        "last_error_text": "",
        "amount": amount,
        "network": network
    })
    _touch_ttl(key)

def _update_stage(key: str, stage_left):
    if not r:
        return
    r.hset(key, mapping={
        "stage": ",".join(stage_left)
    })
    _touch_ttl(key)

def _update_error(key: str, code: str, text: str):
    if not r:
        return
    r.hset(key, mapping={
        "last_error_code": code or "",
        "last_error_text": text or ""
    })
    _touch_ttl(key)

def _parse_stage_list(s: str):
    return [x for x in (s or "").split(",") if x]

async def _advance_fsm_state(username: int, chat_id: int, bot_id: int, next_state, extra: dict | None = None):
    try:
        storage = RedisStorage(redis=AsyncRedis.from_url(REDIS_URL, db=REDIS_DB_FSM))
        logger.info(f"[tasks] _advanc1e_fsm_state storage: -------------------------------------------- {storage}")

        logger.info(f"[tasks] _advance_fsm_state params: {chat_id} ----- {username} ----- {bot_id}")
        key = StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=username)
        logger.info(f"[tasks] _advance_fsm_state key: {key}")
        await storage.set_state(key, next_state)
        current_state = await storage.get_state(key)
        logger.info(f"[tasks] _advance_fsm_state current_state after set: {current_state}")
        data = await storage.get_data(key) or {}
        logger.info(f"[tasks] _advance_fsm_state data: {data}")
        if extra:
            data.update(extra)
        await storage.set_data(key, data)
    except Exception as e:
        logger.error(f"Ошибка в _advance_fsm_state: {e}")

@celery_task_fallback
def check_confirmation_task(tx_hash, target_address, username, chat_id, bot_id, lang, network):
    if not r:
        logger.error("Redis недоступен для check_erc20_confirmation_task")
        return

    key = _redis_key(tx_hash)
    kyiv_tz = ZoneInfo("Europe/Kyiv")
    now = datetime.now(kyiv_tz).strftime("%d.%m.%Y %H:%M:%S")



    try:
        if network == "ERC20":
            stage_set = {"in_block", "is_erc20", "recipient", "transfer_params", "confirmations"}
            logger.info(f"[tasks---check_confirmation_task] ERC20:-------------------------------------------------------------------")          
            result = run_async_coroutine(check_transaction_stages(tx_hash, target_address, stage_set))
        if network == "TRC20":
            logger.info(f"[tasks---check_confirmation_task] TRC20:+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")    
            result = run_async_coroutine(check_tron_transaction(tx_hash, target_address))
        code = result.get("code", "") != "low_confirmations"
        amount = result.get("amount", "N/A")

        logger.info(f"[tasks] check_erc20 result: {result}")

        # сохраняем в Google сразу «как есть»
        google_params = [username, 
                         tx_hash, 
                         target_address, 
                         result.get("timestamp", "N/A"), 
                         now, 
                         result.get("status", "pending"), 
                         amount, 
                         result.get("error", "") if code else ''
                    ]

        save_transaction_hash(google_params)

        if result.get("success") and result.get("status") == "confirmed":
            google_update_params = {"status": [result.get("status"), 6]}
            msg = {
                "msg_status": "tx_confirmed",
                "lang": lang,
                "amount_result": amount,
                "target_address": target_address,
                "timestamp": result.get("timestamp", "N/A"),
            }
            
            update_transaction_status(tx_hash, google_update_params)
            run_async_coroutine(_advance_fsm_state(
                username=username,
                chat_id=chat_id,
                bot_id=bot_id,
                next_state=CryptoFSM.contact,
                extra={
                    "amount_result": amount,
                    "tx_hash": tx_hash,
                    "target_address": target_address,
                    "timestamp": result.get("timestamp", "N/A"),
                },
            ))
            run_async_coroutine(send_telegram_notification(chat_id, msg))
            return
        else:
            if not r.exists(key):
                _store_initial(username, chat_id, bot_id, tx_hash, target_address, lang, amount, network)

        # not success → обновим стадии/ошибку и оставим ключ
        if network == "ERC20":
            stage_left = result.get("stage", [])
            _update_stage(key, stage_left)
            _update_error(key, result.get("code", ""), result.get("error", ""))

        # для «фатальных» кейсов сразу уведомим
        code = result.get("code")
        if code in ("invalid_token", "invalid_recipient"):
            google_update_params = {"status": result.get("status")}
            msg = {                
                "lang": lang,
                "amount_result": amount,
                "target_address": target_address,
                "timestamp": result.get("timestamp", "N/A"),
            }
            if code == "invalid_token":
                msg.update({"msg_status": "invalid_token_erc"})
            else:
                msg.update({"msg_status": "invalid_recipient"})
                
            google_update_params = {"status": [result.get("status"), 6], "error": [result.get("error",""), 8]}
            run_async_coroutine(send_telegram_notification(chat_id, msg))
            update_transaction_status(tx_hash, google_update_params)
            
            r.delete(key)
        else:
            # pending — просто оставляем на periodic beat
            _touch_ttl(key)

    except Exception as e:
        logger.error(f"Ошибка проверки {tx_hash}: {e}")
        if r:
            _update_error(key, "internal_error", str(e))

@celery_task_fallback
def periodic_check_pending_transactions():
    if not r:
        logger.error("Redis недоступен для periodic_check_pending_transactions")
        return
        
    kyiv_tz = ZoneInfo("Europe/Kyiv")
    now = datetime.now(kyiv_tz).strftime("%d.%m.%Y %H:%M:%S")
    
    """
    Периодический обход всех pending транзакций.
    """
    try:
        # keys = r.keys(f"{REDIS_KEY_PREFIX_ERC}*")
        patterns = [f"{REDIS_KEY_PREFIX_ERC}*", f"{REDIS_KEY_PREFIX_TRC}*"]

        for pattern in patterns:
            for key in r.scan_iter(match=pattern):
                tx_data = r.hgetall(key)
                if not tx_data:
                    continue

                tx_hash = key.split(":")[1]
                username = tx_data.get("username")
                lang = tx_data.get("lang")
                chat_id = tx_data.get("chat_id")
                bot_id = tx_data.get("bot_id")
                target_address = tx_data.get("target_address")
                first_seen_str = tx_data.get("first_seen")
                amount = tx_data.get("amount", "N/A")
                network = tx_data.get("network", "N/A")

                if not username or not target_address:
                    logger.warning(f"[BEAT] Пропускаю {key} — нет username/target_address")
                    r.delete(key)
                    continue

                

                try:
                    if network == "ERC20":
                        stage_list = _parse_stage_list(tx_data.get("stage"))
                        stage_set = set(stage_list) if stage_list else {"in_block","is_erc20","recipient","transfer_params","confirmations"}
                        logger.info(f"[tasks---periodic_check_pending_transactions] ERC20:-------------------------------------------------------------------")   
                        result = run_async_coroutine(check_transaction_stages(tx_hash, target_address, stage_set))
                    if network == "TRC20":
                        logger.info(f"[tasks---periodic_check_pending_transactions] TRC20:+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++") 
                        result = run_async_coroutine(check_tron_transaction(tx_hash, target_address))
                    # result = run_async_coroutine(check_transaction_stages(tx_hash, target_address, stage_set))
                    logger.info(f"[BEAT] {tx_hash} result: {result}")

                    if result.get("success") and result.get("status") == "confirmed":
                        if network == "ERC20":
                            google_update_params = {"status": [result.get("status"), 6], "date_confirmation": [now, 5]}
                        if network == "TRC20":
                            google_update_params = {
                                "status": [result.get("status"), 6], 
                                "date_confirmation": [now, 5], 
                                "timestamp": [result.get("timestamp", "N/A"), 4],
                                "amount": [result.get("amount", "N/A"), 7],
                                "error": ['', 8]
                            }
                        msg = {
                            "msg_status": "tx_confirmed",
                            "lang": lang,
                            "amount_result": amount,
                            "target_address": target_address,
                            "timestamp": result.get("timestamp", "N/A"),
                        }
                        run_async_coroutine(send_telegram_notification(chat_id, msg))
                        update_transaction_status(tx_hash, google_update_params)
                        run_async_coroutine(_advance_fsm_state(
                            username=username,
                            chat_id=chat_id,
                            bot_id=bot_id,
                            next_state=CryptoFSM.contact,
                            extra={
                                "amount_result": amount,
                                "tx_hash": tx_hash,
                                "target_address": target_address,
                                "timestamp": result.get("timestamp", "N/A"),
                            },
                        ))
                        r.delete(key)
                        continue

                    # обновим стадии/ошибку
                    if network == "ERC20":
                        _update_stage(key, result.get("stage", []))
                        _update_error(key, result.get("code",""), result.get("error",""))

                    code = result.get("code")

                    # фатальные кейсы — сразу уведомление и чистим
                    if code in ("invalid_token", "invalid_recipient"):
                        google_update_params = {"status": result.get("status")}
                        msg = {                
                            "lang": lang,
                            "amount_result": amount,
                            "target_address": target_address,
                            "timestamp": result.get("timestamp", "N/A"),
                        }
                        if code == "invalid_token":
                            if network == "ERC20":
                                msg.update({"msg_status": "invalid_token_erc"})
                            if network == "TRC20":
                                msg.update({"msg_status": "invalid_token_trc"})
                            
                        else:
                            msg.update({"msg_status": "invalid_recipient"})
                            
                        google_update_params = {"status": [result.get("status"), 6], "error": [result.get("error",""), 8]}
                        run_async_coroutine(send_telegram_notification(chat_id, msg))
                        update_transaction_status(tx_hash, google_update_params)

                        r.delete(key)
                        continue

                    # просрочка ожидания
                    if first_seen_str:
                        first_seen = datetime.fromisoformat(first_seen_str)
                        if datetime.now(timezone.utc) - first_seen > MAX_PENDING_DURATION:
                            msg = {     
                                "msg_status": "expired",           
                                "lang": lang,
                                "amount_result": amount,
                                "target_address": target_address,
                                "timestamp": result.get("timestamp", "N/A"),
                            }
                            error_msg = f"Транзакция удалена: не получено подтверждение в течение 2 часов\n{result.get('error','')}"
                            google_update_params = {"status": ["expired", 6], "date_confirmation": [now, 5], "error": [error_msg, 8]}
                            run_async_coroutine(send_telegram_notification(chat_id, msg))
                            update_transaction_status(tx_hash, google_update_params)

                            r.delete(key)
                            continue

                    # если просто pending — оставляем ключ с продлённым TTL
                    _touch_ttl(key)

                except Exception as e:
                    logger.error(f"[BEAT] Ошибка при проверке {tx_hash}: {e}")
                    _update_error(key, "internal_error", str(e))
                    _touch_ttl(key)

    except Exception as e:
        logger.error(f"[BEAT] Ошибка в periodic_check_pending_transactions: {e}")