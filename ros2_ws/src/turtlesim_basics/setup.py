from setuptools import find_packages, setup

package_name = 'turtlesim_basics'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='howard.jeong',
    maintainer_email='howard.jeong@theplatforms.io',
    description='turtlesim 으로 익히는 ROS 2 기초: Topic(pub/sub) 과 Service(client/server)',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            # Step 2 — Topic
            'pose_listener = turtlesim_basics.pose_listener:main',
            'draw_circle = turtlesim_basics.draw_circle:main',
            'wall_bounce = turtlesim_basics.wall_bounce:main',
            # Step 3 — Service
            'spawn_turtle = turtlesim_basics.spawn_turtle:main',
            'draw_square = turtlesim_basics.draw_square:main',
            'pose_reporter = turtlesim_basics.pose_reporter:main',
        ],
    },
)
