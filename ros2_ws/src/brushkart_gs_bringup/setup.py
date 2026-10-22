import os
from glob import glob

from setuptools import find_packages
from setuptools import setup

package_name = 'brushkart_gs_bringup'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='exedy',
    maintainer_email='skwn.pro@gmail.com',
    description='Launch file untuk seluruh stack ground station Brush Kart.',
    license='Apache-2.0',
    entry_points={'console_scripts': []},
)
