from setuptools import setup, find_packages

setup(
    name="emamutalks",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot>=20.0",
        "python-dotenv>=0.19.0",
        "aiohttp==3.9.1",
        "profanity-check==1.0.3",
    ],
) 