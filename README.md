# 🤖 Starknet Claimer
Бот для клейма и отправки токенов $STRK

## 🚀 Установка и запуск
### ⚒ Установка зависимостей
- Для пользователей 🪟 Windows:
    1. Установите [chocholatey](https://chocolatey.org/install), введя команду, указанную на сайте в PowerShell от имени администратора
    2. Откройте терминал и выполните команду `choco install mingw`
    3. Закройте терминал
- Для пользователей 🐧 Linux:
    1. Откройте терминал и выполните команду `sudo apt install -y libgmp3-dev`
- Для пользователей 🍎 MacOS:
    1. Откройте терминал и выполните команду `brew install gmp`
    2. Для владельцев процессоров M1/M2 выполните команду ``CFLAGS=-I`brew --prefix gmp`/include LDFLAGS=-L`brew --prefix gmp`/lib``

### 🐍 Установка Python
1. Перейдите на [официальный сайт Python 3.11](https://www.python.org/downloads/release/python-3116/)
2. В разделе "Files" выберите подходящий вариант для вашей операционной системы
3. Запустите установщик и обязательно поставьте галочку "Add Python to PATH"

### 🤖 Установка бота
1. На GitHub нажмите кнопку "Code" -> "Download ZIP" и разархивируйте в выбранную папку
2. Откройте терминал и перейдите в папку с ботом: `cd "path/to/bot"`, где `path/to/bot` - путь к папке с ботом
3. Установите все необходимые библиотеки командой `pip install -r requirements.txt`
4. Настройте аккаунты и действия в файле `wallets_dest.xlsx`
5. Настройте файл `config_dest.json`
6. Непосредственно перед запуском переименуйте файлы `wallets_dest.xlsx` и `config_dest.json` в `wallets.xlsx` и `config.json` соответственно
7. Запустите бота командой: `python main.py`

## 📋 Как настроить `wallets.xlsx`
В файле `wallets.xlsx` находится несколько столбцов:
- `Private key` - приватные ключи аккаунтов
- `Address` - адреса аккаунтов
- `Proxy` - прокси для аккаунтов в формате `login:password@host:port`
- `Deposit address` - адреса, на которые нужно вывести токены

## ⚙️ Как настроить `config.json`
В файле `config.json` находятся такие параметры:
- `threads` - количество потоков для работы бота
- `max_retries` - сколько раз бот будет пытаться выполнить действия перед тем, как перейдёт к следующему аккаунту
- `rpc_url` - адрес RPC ноды Starknet (по умолчанию используется наша приватная нода)
- `comission_mode` - режим комиссии. По умолчанию установлен параметр `default` - вся комиссия (3%) будет отправляться на один и тот же адрес. Опционально можно вместо `default` установить значение `server`: тогда для каждого аккаунта будет использоваться свой адрес для комиссии

## 🙏 Поддержка
Если вы хотите поддержать разработчика, вот адреса:
- Metamask: `0x352b0ca91C67Ad1d15e792EA574E6ccf2418Cc56`
- Starknet: `0x021c6871f441871cb6eeea2312db8f4e277cf42095ec9f346d11b54838abe919`
