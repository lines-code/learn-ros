"""미로 월드 + TurtleBot3(burger) + (선택) 주행 노드를 한 번에 실행한다.

  ros2 launch turtlebot3_maze maze.launch.py                              # 미로 + 로봇만
  ros2 launch turtlebot3_maze maze.launch.py navigator:=wall_follower     # 오른손 법칙
  ros2 launch turtlebot3_maze maze.launch.py navigator:=jev_navigator     # OpenJev 판단
  ros2 launch turtlebot3_maze maze.launch.py gui:=false                   # 화면 없이 (CPU 절약)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

NAVIGATORS = ['wall_follower', 'jev_navigator', 'obstacle_avoider']


def generate_launch_description():
    # turtlebot3_gazebo 의 launch 파일이 이 환경변수를 읽는다. docker exec 로 실행하면 .bashrc 가 없으므로 기본값을 둔다.
    os.environ.setdefault('TURTLEBOT3_MODEL', 'burger')
    model = os.environ['TURTLEBOT3_MODEL']

    pkg = get_package_share_directory('turtlebot3_maze')
    tb3 = get_package_share_directory('turtlebot3_gazebo')
    gz_launch = os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
    world = os.path.join(pkg, 'worlds', 'maze.sdf')

    gui = LaunchConfiguration('gui')
    x = LaunchConfiguration('x_pose')
    y = LaunchConfiguration('y_pose')
    navigator = LaunchConfiguration('navigator')

    args = [
        DeclareLaunchArgument('gui', default_value='true', description='Gazebo 화면 표시'),
        DeclareLaunchArgument('x_pose', default_value='-2.0', description='출발 x (칸 (0,0) 중심)'),
        DeclareLaunchArgument('y_pose', default_value='-2.0', description='출발 y'),
        DeclareLaunchArgument('navigator', default_value='none',
                              description='none | ' + ' | '.join(NAVIGATORS)),
        DeclareLaunchArgument('use_openjev', default_value='true',
                              description='jev_navigator 가 OpenJev 를 쓸지 (false 면 오른손 법칙)'),
        DeclareLaunchArgument('openjev_url', default_value='http://host.docker.internal:31001'),
    ]

    sim = [
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', os.path.join(tb3, 'models')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_launch),
            launch_arguments={'gz_args': ['-r -s -v2 ', world], 'on_exit_shutdown': 'true'}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_launch),
            launch_arguments={'gz_args': '-g -v2 ', 'on_exit_shutdown': 'true'}.items(),
            condition=IfCondition(gui)),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(tb3, 'launch', 'robot_state_publisher.launch.py')),
            launch_arguments={'use_sim_time': 'true'}.items()),
        Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=['-name', model,
                       '-file', os.path.join(tb3, 'models', f'turtlebot3_{model}', 'model.sdf'),
                       '-x', x, '-y', y, '-z', '0.01']),
        Node(
            package='ros_gz_bridge', executable='parameter_bridge', output='screen',
            arguments=['--ros-args', '-p',
                       'config_file:=' + os.path.join(tb3, 'params', f'turtlebot3_{model}_bridge.yaml')]),
    ]

    nav_params = {'use_sim_time': True}
    navs = [
        Node(
            package='turtlebot3_maze', executable=name, output='screen',
            # x_pose:=0 처럼 넘겨도 int 로 해석되지 않도록 타입을 고정한다
            parameters=[nav_params, {'start_x': ParameterValue(x, value_type=float),
                                     'start_y': ParameterValue(y, value_type=float),
                                     'use_openjev': ParameterValue(LaunchConfiguration('use_openjev'),
                                                                   value_type=bool),
                                     'openjev_url': LaunchConfiguration('openjev_url')}
                        if name == 'jev_navigator' else nav_params],
            condition=IfCondition(PythonExpression(["'", navigator, f"' == '{name}'"])))
        for name in NAVIGATORS
    ]

    return LaunchDescription(args + sim + navs)
