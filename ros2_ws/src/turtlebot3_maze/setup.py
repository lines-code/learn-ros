from glob import glob

from setuptools import find_packages, setup

package_name = 'turtlebot3_maze'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/worlds', glob('worlds/*.sdf')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='howard.jeong',
    maintainer_email='howard.jeong@theplatforms.io',
    description='Gazebo + TurtleBot3 미로: LiDAR 장애물 회피, 벽 따라가기, OpenJev 판단 기반 미로 탈출',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Step 2 — LiDAR
            'scan_viewer = turtlebot3_maze.scan_viewer:main',
            'obstacle_avoider = turtlebot3_maze.obstacle_avoider:main',
            # Step 3 — 미로
            'wall_follower = turtlebot3_maze.wall_follower:main',
            # 고도화 — OpenJev 판단
            'jev_navigator = turtlebot3_maze.jev_navigator:main',
        ],
    },
)
