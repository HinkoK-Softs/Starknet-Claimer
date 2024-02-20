import dataclasses
import json
import re
import warnings
from pathlib import Path

import pandas as pd

import utils
from logger import logging

def shorten_private_key(private_key: str) -> str:
    if len(private_key) <= 16:
        return private_key
    return f'{private_key[:8]}...{private_key[-8:]}'


@dataclasses.dataclass
class BotAccount:
    private_key: str
    address: str
    proxy: str
    deposit_address: str
    amount: int

    @property
    def short_private_key(self):
        return shorten_private_key(self.private_key)


def read_accounts() -> list[BotAccount]:
    warnings.filterwarnings(
        'ignore',
        category=UserWarning,
        module='openpyxl'
    )
    pd.set_option('future.no_silent_downcasting', True)

    logging.info('[Account Loader] Loading accounts')

    with open('eligibilities.json') as file:
        eligibilities = json.load(file)

    with open('claimed.json') as file:
        claimed = json.load(file)

    accounts = []

    default_account_values = {}
    for field in dataclasses.fields(BotAccount):
        if field.default != dataclasses.MISSING:
            default_account_values[field.name] = field.default

    acounts_file_path = Path(__file__).parent / 'wallets.xlsx'

    if not acounts_file_path.exists():
        logging.error(f'[Account Loader] File "{acounts_file_path.name}" does not exist')
        return False

    accounts_file = pd.ExcelFile(acounts_file_path)
    sheets = [sheet.lower() for sheet in accounts_file.sheet_names]
    del accounts_file

    dtypes = {
        'Private key': str,
        'Address': str,
        'Proxy': str,
        'Deposit address': str
    }

    accounts_df = pd.read_excel(
        acounts_file_path,
        dtype=dtypes
    )
    accounts_df = accounts_df.apply(lambda x: x.str.strip() if x.dtype == object else x)
    accounts_df.columns = ['_'.join(column.lower().split(' ')) for column in accounts_df.columns]
    unknown_account_columns = set(accounts_df.columns) - {field.name for field in dataclasses.fields(BotAccount)}

    if unknown_account_columns:
        logging.error(f'[Account Loader] Unknown account columns: {", ".join(unknown_account_columns)}')
        return False

    accounts_df.dropna(subset=['private_key', 'address'], inplace=True, how='all')
    for column in accounts_df.columns:
        if column in default_account_values:
            accounts_df[column] = accounts_df[column].fillna(
                default_account_values[column]
            )
        else:
            accounts_df[column] = accounts_df[column].fillna(-31294912).replace(-31294912, None)

    for row in accounts_df.itertuples():
        row_address = utils.extend_hex(row.address, 64)

        if row_address.lower() not in eligibilities:
            logging.warning(f'[Account Loader] Address "{row_address}" is not eligible')
            continue
        if row_address.lower() in claimed:
            logging.warning(f'[Account Loader] Address "{row_address}" is already claimed')
            continue

        if not row.private_key:
            logging.error(f'[Account Loader] Missing private key on row {row.Index + 1}')
            return False

        if not row_address:
            logging.error(f'[Account Loader] Missing address on row {row.Index + 1}')
            return False
        elif not row.deposit_address:
            logging.error(f'[Account Loader] Missing deposit address on row {row.Index + 1}')
            return False
        elif not re.match(r'^(0x)?[a-fA-F0-9]+$', row.private_key):
            short_private_key = shorten_private_key(row.private_key)
            logging.error(f'[Account Loader] Invalid private key "{short_private_key}" on row {row.Index + 1}')
            return False
        elif not re.match(r'^(0x)?[a-fA-F0-9]+$', row_address):
            logging.error(f'[Account Loader] Invalid address "{row_address}" on row {row.Index + 1}')
            return False

        if row.proxy:
            if re.match(r'(socks5|http)://', row.proxy):
                proxy = {
                    'http': row.proxy,
                    'https': row.proxy
                }
            elif '/' not in row.proxy:
                proxy = {
                    'http': f'http://{row.proxy}',
                    'https': f'http://{row.proxy}'
                }
            else:
                logging.error(f'[Account Loader] Invalid proxy "{row.proxy}"')
                return False
        else:
            proxy = None

        try:
            account = BotAccount(
                private_key=row.private_key,
                address=row_address,
                proxy=proxy,
                deposit_address=row.deposit_address,
                amount=eligibilities[row_address.lower()]
            )
        except AttributeError as e:
            res = re.search("has no attribute '(?P<attribute>.+)'", str(e))
            if res:
                attribute = res.group('attribute')
                logging.error(f'[Account Loader] Missing {attribute} column')
            else:
                logging.error(f'[Account Loader] Failed to load account: {e}')
            return
        accounts.append(account)

    return accounts
