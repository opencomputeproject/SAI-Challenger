from setuptools import setup

setup(
    name="sai-challenger",
    version='0.1',
    description='SAI Challenger core library',
    license='Apache 2.0',
    author='Andriy Kokhan',
    author_email='andriy.kokhan@gmail.com',
    url='https://github.com/PLVision/sai-challenger',
    install_requires=[
        'ptf',
    ],
    py_modules=['sai', 'sai_npu', 'sai_dataplane', 'sai_environment', 'sai_abstractions', 'sai_dpu', 'sai_data', 'sai_object'],
)
