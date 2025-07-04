from setuptools import setup, find_packages

setup(
    name='pyims',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'pycryptodome'
    ],
    author='Tom Tzook',
    author_email='tomtzook@gmail.com',
    description='IMS Communication for Python'
)
