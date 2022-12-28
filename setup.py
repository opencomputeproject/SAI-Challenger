from setuptools import setup

setup(
    name="sai-challenger-extensions",
    version='0.1',
    description='SAI Challenger CLI & basic topologies',
    license='Apache 2.0',
    author='Andriy Kokhan',
    author_email='andriy.kokhan@gmail.com',
    url='https://github.com/opencomputeproject/SAI-Challenger',
    install_requires=[
        'click==8.0',
    ],
    packages=[
        'saichallenger.cli',
        'saichallenger.topologies',
    ],
    package_dir={
        'saichallenger.cli': 'cli',
        'saichallenger.topologies': 'topologies',
    },
    scripts=[
        'scripts/redis-cmd-listener.py'
    ],
    entry_points={
        'console_scripts': [
            'sai = saichallenger.cli.main:cli',
        ]
    },
)
