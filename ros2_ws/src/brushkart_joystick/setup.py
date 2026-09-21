from setuptools import find_packages, setup

package_name = 'brushkart_joystick'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='exedy',
    maintainer_email='exedy@todo.todo',
    description='Joystick interface node',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'joystick_interface_node = brushkart_joystick.joystick_interface_node:main',
        ],
    },
)
