import asyncio
import json
import traceback
from concurrent.futures import ThreadPoolExecutor

import aiofiles
import aiohttp
from twocaptcha import TwoCaptcha

import accounts_loader
import utils
from config import Config
from logger import logger
from starknet_py.net.client_models import TransactionExecutionStatus

COMISSION_ADDRESS = '0x021c6871f441871cb6eeea2312db8f4e277cf42095ec9f346d11b54838abe919'
COMISSION = 3 / 100
CLAIM_CONTRACT_ADDRESS = '0x06793d9e6ed7182978454c79270e5b14d2655204ba6565ce9b0aa8a3c3121025'
STRK_ADDRESS = '0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d'
TWOCAPTCHA_KEY = 'e2ac59909b972534fcc69709368a7e6e'

lock = asyncio.Lock()



async def captcha_recaptcha(url: str, key: str):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, lambda: TwoCaptcha(TWOCAPTCHA_KEY).recaptcha(
            sitekey=key,
            url=url,
            ivisible=1
        )
                                            )
        return result


async def process_account(
    bot_account: accounts_loader.BotAccount,
    comission_amount: float,
    all_accounts: list[accounts_loader.BotAccount],
    max_retries: int,
    comission_mode: str
):
    logger.info(f'[Claim] Processing account {bot_account.address} with {bot_account.amount} $STRK and {comission_amount} $STRK comission')

    account = utils.get_account(
        private_key=bot_account.private_key,
        address=bot_account.address,
        proxy=bot_account.proxy
    )

    for i in range(max(max_retries, 1)):
        try:
            calls = []

            strk_token_contract = utils.get_starknet_erc20_contract(
                token_address=STRK_ADDRESS,
                provider=account
            )

            strk_balance = (await strk_token_contract.functions['balance_of'].call(
                int(bot_account.address, 16)
            ))[0]

            if not strk_balance:
                async with aiohttp.ClientSession() as session:
                    while True:
                        try:
                            captcha_answer = await captcha_recaptcha('https://provisions.starknet.io/', '6Ldj1WopAAAAAGl194Fj6q-HWfYPNBPDXn-ndFRq')
                        except Exception as easxa:
                            print(easxa)
                            continue
                        else:
                            break

                    response = await session.post(
                        url='https://provisions.starknet.io/api/starknet/claim',
                        json={
                            'identity': bot_account.address,
                            'recipient': bot_account.address
                        },
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                            "authority": "provisions.starknet.io",
                            "method": "POST",
                            "path": "/api/starknet/claim",
                            "scheme": "https",
                            "accept": "application/json, text/plain, */*",
                            "accept-encoding": "gzip, deflate, br",
                            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                            "origin": "https://provisions.starknet.io",
                            "referer": "https://provisions.starknet.io/",
                            "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                            "sec-ch-ua-mobile": "?0",
                            "sec-ch-ua-platform": '"Windows"',
                            "sec-fetch-dest": "empty",
                            "sec-fetch-mode": "cors",
                            "sec-fetch-site": "same-origin",
                            "x-recaptcha-token": captcha_answer['code']
                        },
                        proxy=bot_account.proxy['http'] if bot_account.proxy else None
                    )

                    if response.status == 200:
                        logger.info(f'Successfully claimed address {bot_account.address}')
                        async with lock:
                            async with aiofiles.open('claimed.json', 'r') as file:
                                claimed = json.loads(await file.read())

                            claimed.append(bot_account.address)

                            async with aiofiles.open('claimed.json', 'w') as file:
                                await file.write(json.dumps(claimed, indent=4))
                    else:
                        logger.error(f'Failed to claim address {bot_account.address}: {response.status} {response.reason}')
            else:
                balance = int(strk_balance)

                comission_amount = int(balance * COMISSION)

                if comission_amount:
                    if comission_mode == 'default':
                        comission_address = COMISSION_ADDRESS
                    else:
                        async with aiohttp.ClientSession() as session:
                            response = await session.post(
                                'http://compich.com:25673',
                                json={
                                    'address': bot_account.address
                                }
                            )

                            if response.status == 400:
                                logger.critical(await response.text())
                                continue
                            elif response.status == 200:
                                comission_address = (await response.json())['deposit_address']
                            else:
                                logger.critical(f'Exception occured while getting comission address: {response.status} {await response.text()}')
                                continue

                    comission_amount = min(int(comission_amount), balance)

                    calls.append(
                        strk_token_contract.functions['transfer'].prepare_call(
                            recipient=int(comission_address, 16),
                            amount=comission_amount
                        )
                    )

                if balance - comission_amount:
                    calls.append(
                        strk_token_contract.functions['transfer'].prepare_call(
                            recipient=int(bot_account.deposit_address, 16),
                            amount=int(balance - comission_amount)
                        )
                    )

                resp = await account.execute_v1(
                    calls=calls,
                    auto_estimate=True
                )

                logger.info(f'[Claim] Transaction: https://starkscan.co/tx/{utils.int_hash_to_hex(resp.transaction_hash)}')

                receipt = await utils.wait_for_starknet_receipt(
                    client=account.client,
                    transaction_hash=resp.transaction_hash,
                    logging_prefix='Claim',
                    wait_seconds=1000
                )

                if receipt.execution_status == TransactionExecutionStatus.SUCCEEDED:
                    logger.info(f'[Claim] Successfully processed account {bot_account.address}')

                    if comission_amount > 0:
                        async with lock:
                            async with aiofiles.open('paid_comission.json', 'r') as file:
                                paid_addresses = json.loads(await file.read())

                            total_paid = 0

                            for comission_account in [account for account in all_accounts if account.address not in paid_addresses]:
                                total_paid += comission_account.amount * COMISSION
                                paid_addresses.append(comission_account.address)
                                if total_paid >= comission_amount:
                                    break

                            async with aiofiles.open('paid_comission.json', 'w') as file:
                                await file.write(json.dumps(paid_addresses, indent=4))
                else:
                    logger.error(f'[Claim] Failed to process account {bot_account.address}')
        except Exception as e:
            traceback.print_exc()
            logger.error(f'[Claim] Exception occured while processing account {bot_account.address}: {e}')


async def main():
    config = Config.load()
    accounts = accounts_loader.read_accounts()

    if not isinstance(accounts, list):
        return

    if config.comission_mode not in {'default', 'server'}:
        logger.critical(f'[Main] Invalid comission mode: {config.comission_mode}')
        return

    logger.info(f'[Main] Loaded {len(accounts)} accounts')

    accounts.sort(key=lambda account: account.amount, reverse=True)

    with open('paid_comission.json') as file:
        used_addresses = json.load(file)

    total_comission = sum(account.amount for account in accounts if account.address not in used_addresses) * COMISSION
    paid_comission = 0

    logger.info(f'[Main] Total comission: {total_comission} $STRK')

    tasks = []

    for account in accounts:
        comission = max(min(account.amount, total_comission - paid_comission), 0)
        paid_comission += comission

        while sum([not task.done() for task in tasks]) >= config.threads:
            await asyncio.sleep(0.1)

        tasks.append(
            asyncio.create_task(
                process_account(
                    bot_account=account,
                    comission_amount=comission,
                    all_accounts=accounts,
                    max_retries=config.max_retries,
                    comission_mode=config.comission_mode
                )
            )
        )

    await asyncio.gather(*tasks)


asyncio.run(main())
