from setuptools import setup, find_packages

# get version from __version__ variable in commission_record/__init__.py
from commission_record import __version__ as version

setup(
    name="commission_record",
    version=version,
    description="用于记录额外的分成",
    author="舍满取半",
    author_email="qdsmqb@163.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[],
)
