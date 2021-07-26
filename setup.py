from setuptools import setup

setup(
    name="sai-challenger-cli",
    version='0.1',
    description='Command-line utilities for SAI Challenger',
    license='Apache 2.0',
    author='Andriy Kokhan',
    author_email='andriy.kokhan@gmail.com',
    url='https://github.com/PLVision/sai-challenger',
    install_requires=[
        'click==7.0',
    ],
    packages=['cli'],
    entry_points={
        'console_scripts': [
            'sai = cli.main:cli',
        ]
    },
)
