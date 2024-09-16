from pyrogram.raw.functions.messages import RequestWebView
from urllib.parse import unquote
from fake_useragent import UserAgent
from pyrogram import Client
from data import config
from ..utils.core import logger
from datetime import datetime

import aiohttp
import asyncio
import random


class TimeFarm:

    def __init__(self, thread: int, account: str, proxy=None):
        self.thread = thread
        self.name = account
        if proxy:
            proxy_client = {
                "scheme": config.PROXY_TYPE,
                "hostname": proxy.split(':')[0],
                "port": int(proxy.split(':')[1]),
                "username": proxy.split(':')[2],
                "password": proxy.split(':')[3],
            }
            self.client = Client(name=account, api_id=config.API_ID, api_hash=config.API_HASH, workdir=config.WORKDIR,
                                 proxy=proxy_client)
        else:
            self.client = Client(name=account, api_id=config.API_ID, api_hash=config.API_HASH, workdir=config.WORKDIR)

        if proxy:
            self.proxy = f"{config.PROXY_TYPE}://{proxy.split(':')[2]}:{proxy.split(':')[3]}@{proxy.split(':')[0]}:{proxy.split(':')[1]}"
        else:
            self.proxy = None

        self.auth_token = ""
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'origin': 'https://timefarm.app',
            'referer': 'https://timefarm.app/',
            'priority': 'u=1, i',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': UserAgent(os='ios').random}

        self.session = aiohttp.ClientSession(headers=headers, trust_env=True,
                                             connector=aiohttp.TCPConnector(verify_ssl=False))

    async def get_tg_web_data(self):
        await self.client.connect()
        try:
            web_view = await self.client.invoke(RequestWebView(
                peer=await self.client.resolve_peer('TimeFarmCryptoBot'),
                bot=await self.client.resolve_peer('TimeFarmCryptoBot'),
                platform='android',
                from_bot_menu=False,
                url='https://timefarm.app/'
            ))

            auth_url = web_view.url
        except Exception as err:
            logger.error(f"main | Thread {self.thread} | {self.name} | {err}")
            if 'USER_DEACTIVATED_BAN' in str(err):
                logger.error(f"login | Thread {self.thread} | {self.name} | USER BANNED")
                await self.client.disconnect()
                return False
        await self.client.disconnect()
        return unquote(string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))

    async def login(self):
        try:
            tg_web_data = await self.get_tg_web_data()
            if tg_web_data is False:
                return False
            url = "https://tg-bot-tap.laborx.io/api/v1/auth/validate-init/v2"
            json_data = {"initData": tg_web_data, "platform": "ios"}
            response = await self.session.post(url, json=json_data, proxy=self.proxy)
            if response.status == 200:
                response = await response.json()
                self.session.headers['authorization'] = "Bearer " + response.get("token")
                return True
            return False

        except Exception as err:
            logger.error(f"login | Thread {self.thread} | {self.name} | {err}")
            if err == "Server disconnected":
                return True
            return False

    async def is_token_valid(self):
        url = "https://tg-bot-tap.laborx.io/api/v1/referral/link"
        response = await self.session.get(url, proxy=self.proxy)
        if response.status == 200:
            return True
        elif response.status == 403:
            return False

    async def tasks(self):
        url = "https://tg-bot-tap.laborx.io/api/v1/tasks"
        response = await self.session.get(url=url, proxy=self.proxy)
        if response.status == 200:
            return await response.json()

        return {}

    async def info(self):
        url = "https://tg-bot-tap.laborx.io/api/v1/farming/info"
        response = await self.session.get(url=url, proxy=self.proxy)
        await asyncio.sleep(1)
        if response.status == 200:
            return await response.json()

    async def link(self):
        url = "https://tg-bot-tap.laborx.io/api/v1/referral/link"
        await self.session.get(url=url, proxy=self.proxy)
        await asyncio.sleep(1)

    async def balance(self):
        url = "https://tg-bot-tap.laborx.io/api/v1/balance"
        response = await self.session.get(url=url, proxy=self.proxy)
        await asyncio.sleep(1)
        if response.status == 200:
            response = await response.json()
            return response

        return {}

    async def active(self) -> dict:
        url = "https://tg-bot-tap.laborx.io/api/v1/staking/active"
        response = await self.session.get(url=url, proxy=self.proxy)
        await asyncio.sleep(1)
        if response.status == 200:
            response = await response.json()
            return response.get("stakes")
        return {}

    async def finish_farming(self, max_attempts: int):
        url = "https://tg-bot-tap.laborx.io/api/v1/farming/finish"
        for _ in range(max_attempts):
            response = await self.session.post(url=url, json={},proxy=self.proxy)
            if response.status == 200:
                logger.success(f"main | Thread {self.thread} | {self.name} | Farming successfully completed! ")
                await asyncio.sleep(2)
                return True
            else:
                response = await response.json()
                if response.get("error").get("message") == "Farming didn't start":
                    logger.info(f"main | Thread {self.thread} | {self.name} | Farming didn't start!")
                    return True
                if response.get("error").get("message") == "Too early to finish farming":
                    logger.info(f"main | Thread {self.thread} | {self.name} | Farming isn't over yet!")
                    await asyncio.sleep(2)
                    return False
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to complete the farming!")
        return False

    async def start_farming(self, max_attempts: int):
        url = "https://tg-bot-tap.laborx.io/api/v1/farming/start"
        for _ in range(max_attempts):
            response = await self.session.post(url=url, json={}, proxy=self.proxy)
            if response.status == 200:
                logger.success(f"main | Thread {self.thread} | {self.name} | Farming successfully started! ")
                await asyncio.sleep(2)
                return True
            else:
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to start the farming!")
        return False

    async def claim_referral(self, max_attempts: int):
        url = "https://tg-bot-tap.laborx.io/api/v1/balance/referral/claim"
        for _ in range(max_attempts):
            response = await self.session.post(url=url, proxy=self.proxy)
            if response.status == 201:
                logger.success(f"main | Thread {self.thread} | {self.name} | Points for friends successfully received!")
                await asyncio.sleep(2)
                return True
            else:
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to claim referral points!")
        return False

    async def claim_staking(self, id_staking: str, max_attempts: int):
        url = "https://tg-bot-tap.laborx.io/api/v1/staking/claim"
        body = {"id": id_staking}
        for _ in range(max_attempts):
            response = await self.session.post(url=url, json=body, proxy=self.proxy)
            if response.status == 200:
                logger.success(f"main | Thread {self.thread} | {self.name} | Staking reward successfully received!")
                await asyncio.sleep(2)
                return True
            else:
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to get staking reward!")
        return False

    async def start_staking(self, amount: str, max_attempts: int):
        url = "https://tg-bot-tap.laborx.io/api/v1/staking"
        body = {"optionId": "1", "amount": str(amount)}
        for _ in range(max_attempts):
            response = await self.session.post(url=url, json=body, proxy=self.proxy)
            if response.status == 200:
                logger.success(f"main | Thread {self.thread} | {self.name} | Staking reward successfully received!")
                await asyncio.sleep(2)
                return True
            else:
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to get staking reward!")
        return False

    async def staking(self):
        stakes_info = await self.active()
        await asyncio.sleep(1.5)
        if stakes_info:
            for i in stakes_info:
                if datetime.strptime(i.get("finishAt"), "%Y-%m-%dT%H:%M:%S.%fZ") < datetime.utcnow():
                    await self.claim_staking(i["id"], 3)

        await asyncio.sleep(1)
        balance_points = await self.balance()
        balance_points = balance_points.get("balance")
        await asyncio.sleep(1.5)
        if balance_points and balance_points >= 1000000:
            await self.start_staking(balance_points - 1, 3)

        await self.balance()
        await self.active()

    async def submission(self, task_id: str, title: str, max_attempts: int):
        url = f"https://tg-bot-tap.laborx.io/api/v1/tasks/{task_id}/submissions"
        body = {"result": {"status": "COMPLETED"}}
        for _ in range(max_attempts):
            response = await self.session.post(url=url, json=body, proxy=self.proxy)
            if response.status == 200:
                logger.success(f"main | Thread {self.thread} | {self.name} | Submission task sent: {title}")
                await asyncio.sleep(3)
                return True
            else:
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to sent submission task: {title}")
        return False

    async def claim_task(self, task_id: str, title: str, max_attempts: int):
        url = f"https://tg-bot-tap.laborx.io/api/v1/tasks/{task_id}/claims"
        for _ in range(max_attempts):
            response = await self.session.post(url=url, proxy=self.proxy)
            if response.status == 200:
                logger.success(
                    f"main | Thread {self.thread} | {self.name} | The tasks points have been  claimed: {title}")
                await asyncio.sleep(2)
                return True
            else:
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to claim tasks points: {title}")
        return False


    async def check_tasks(self):
        tasks_info = await self.tasks()
        if tasks_info:
            for i in tasks_info:
                if "submission" not in i:
                    await self.submission(i["id"], i["title"], 3)
                    await self.tasks()

            tasks_info = await self.tasks()
            if tasks_info:
                for i in tasks_info:
                    if i["submission"]["status"] == "COMPLETED":
                        await self.claim_task(i["id"], i["title"], 3)
                        await self.tasks()

    async def referral_claim(self, max_attempts: int):
        url = f"https://tg-bot-tap.laborx.io/api/v1/balance/referral/claim"
        for _ in range(max_attempts):
            response = await self.session.post(url=url, json={}, proxy=self.proxy)
            if response.status == 200:
                logger.success(
                    f"main | Thread {self.thread} | {self.name} | The points for referral successfully claimed!")
                await asyncio.sleep(2)
                return True
            else:
                await asyncio.sleep(2)

        logger.warning(f"main | Thread {self.thread} | {self.name} | Failed to claim referral points!")
        return False

    async def main(self):
        # accounts_dict = self.get_data_from_file()  # {"Account Name":["query","user-agent"]}
        await asyncio.sleep(random.randint(*config.ACC_DELAY))
        try:
            login = await self.login()
            if login is False:
                await self.session.close()
                return 0
            logger.info(f"main | Thread {self.thread} | {self.name} | Start! | PROXY : {self.proxy}")
        except Exception as err:
            logger.error(f"main | Thread {self.thread} | {self.name} | {err}")
            await self.session.close()
            return 0

        try:
            valid = await self.is_token_valid()
            if not valid:
                logger.warning(f"main | Thread {self.thread} | {self.name} | Token is invalid. Refreshing token...")
                if "authorization" in self.session.headers:
                    del self.session.headers['authorization']
                await self.login()

            await asyncio.sleep(2)

            await self.tasks()
            await self.info()
            await self.link()
            await self.balance()
            await self.active()

            if await self.finish_farming(3):
                await self.start_farming(3)

            await asyncio.sleep(random.randint(*config.MINI_SLEEP))

            await self.staking()

            await asyncio.sleep(random.randint(*config.MINI_SLEEP))

            await self.check_tasks()

            await asyncio.sleep(2)

            referral_points = await self.balance()
            referral_points = referral_points.get("referral").get("availableBalance")
            if referral_points and (referral_points >= 10000):
                await self.referral_claim(3)

            await self.session.close()
            await asyncio.sleep(random.randint(*config.MINI_SLEEP))
            # clear_console()
        except Exception as err:
            logger.error(f"main | Thread {self.thread} | {self.name} | {err}")
            if err != "Server disconnected":
                valid = await self.is_token_valid()
                if not valid:
                    logger.warning(f"main | Thread {self.thread} | {self.name} | Token is invalid. Refreshing token...")
                    if "authorization" in self.session.headers:
                        del self.session.headers['authorization']
                    await self.login()
                await asyncio.sleep(random.randint(*config.MINI_SLEEP))
            else:
                await asyncio.sleep(5 * random.randint(*config.MINI_SLEEP))
