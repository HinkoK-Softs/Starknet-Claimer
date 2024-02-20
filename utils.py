import contextlib
import datetime as dt
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Union

import aiohttp

# import constants
# import enums

from config import Config
from logger import logging
from starknet_py.cairo.felt import decode_shortstring
from starknet_py.common import int_from_bytes
from starknet_py.contract import Contract
from starknet_py.net.account.account import Account
from starknet_py.net.client_models import TransactionReceipt
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.models import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair, StarkCurveSigner
from starknet_py.transaction_errors import TransactionRejectedError, TransactionNotReceivedError, TransactionRevertedError

config = Config.load()


def get_account(
    private_key: str,
    address: str,
    proxy: dict[str, str] = None,
    signer_class=None
) -> Account:
    client = FullNodeClient(
        config.rpc_url,
        proxy=proxy if proxy is None else proxy['http']
    )

    key_pair = KeyPair.from_private_key(
        key=private_key
    )

    if signer_class is None:
        signer_class = StarkCurveSigner

    chain_id = StarknetChainId.MAINNET

    signer = signer_class(
        account_address=address,
        key_pair=key_pair,
        chain_id=chain_id
    )

    return Account(
        client=client,
        address=address,
        signer=signer,
        chain=chain_id
    )


def get_starknet_contract(
    address: str,
    abi: list,
    provider: Account
) -> Contract:
    return Contract(
        address=address,
        abi=abi,
        provider=provider,
        cairo_version=1
    )


def sleep(sleep_time: float):
    logging.info(f'[Sleep] Sleeping for {round(sleep_time, 2)} seconds. If you want to skip this, press Ctrl+C')
    try:
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        logging.info('[Sleep] Skipping sleep')


def random_sleep():
    min_sleep_time = getattr(random_sleep, 'min_sleep_time', 1)
    max_sleep_time = getattr(random_sleep, 'max_sleep_time', 10)
    sleep_time = round(random.uniform(min_sleep_time, max_sleep_time), 2)
    sleep(sleep_time)


async def test_proxy(proxy: dict[str, str]) -> str | bool:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            response = await session.get(
                url='https://geo.geosurf.io/',
                proxy=proxy
            )
    except KeyboardInterrupt:
        raise
    except Exception:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                response = await session.get(
                    url='https://google.com',
                    proxy=proxy
                )
        except KeyboardInterrupt:
            raise
        except Exception as e:
            return False
        else:
            return True
    else:
        ip_json = await response.json()
        if 'ip' in ip_json:
            ip = ip_json['ip']
            country = ip_json['country']
            return f'{ip} ({country})'
        else:
            return True


def extend_hex(hex_str: str | int, length: int) -> str:
    if isinstance(hex_str, int):
        hex_str = hex(hex_str)
    return hex_str.replace('0x', '0x' + '0' * (length - len(hex_str) + 2))


def get_starknet_erc20_contract(
    token_address: str,
    provider: Account
) -> Contract:
    with open(Path(__file__).parent / 'abi' / 'STARKNET_ERC20.json') as file:
        erc20_abi = json.load(file)

    return get_starknet_contract(
        address=token_address,
        abi=erc20_abi,
        provider=provider
    )


def int_hash_to_hex(hast_int: int, hash_lenght: int = 64) -> str:
    hash_hex = hex(hast_int)[2:]
    hash_hex = hash_hex.rjust(hash_lenght, '0')
    return f'0x{hash_hex}'


async def wait_for_starknet_receipt(
    client: FullNodeClient,
    transaction_hash: int,
    wait_seconds: float = 300,
    logging_prefix: str = 'Receipt'
) -> TransactionReceipt:
    start_time = time.time()
    while True:
        try:
            return await client.wait_for_tx(transaction_hash)
        except (TransactionRejectedError, TransactionNotReceivedError, TransactionRevertedError):
            raise
        except BaseException as e:
            if time.time() - start_time > wait_seconds:
                input(f'[{logging_prefix}] Failed to get transaction receipt. Press Enter when transaction will be processed')
                try:
                    return await client.wait_for_tx(transaction_hash)
                except BaseException as new_e:
                    logging.error(f'[{logging_prefix}] Failed to get transaction receipt: {new_e}')
                    raise
            logging.warning(f'[{logging_prefix}] Error while getting transaction receipt: {e}')
