from setuptools import setup, find_packages

print(find_packages(''))
setup(
    name="sai-challenger",
    version='0.1',
    description='SAI Challenger core library',
    license='Apache 2.0',
    author='Andriy Kokhan',
    author_email='andriy.kokhan@gmail.com',
    url='https://github.com/opencomputeproject/SAI-Challenger',
    install_requires=[
        'ptf',
    ],
    packages=[
        'saichallenger.common',
        'saichallenger.common.sai_client',
        'saichallenger.common.sai_client.sai_redis_client',
        'saichallenger.common.sai_client.sai_thrift_client',
    ],
    package_dir={
        'saichallenger.common': '',
    },
)
