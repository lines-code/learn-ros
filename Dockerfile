# noVNC 데스크톱이 포함된 ROS 2 Jazzy 이미지 (amd64 / arm64 모두 제공)
FROM tiryoh/ros2-desktop-vnc:jazzy

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-pip python3-colcon-common-extensions \
      ros-jazzy-turtlesim ros-jazzy-rqt* \
      ros-jazzy-cv-bridge ros-jazzy-image-transport ros-jazzy-image-publisher \
      ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
      ros-jazzy-ros-gz \
      ros-jazzy-turtlebot3* \
    && rm -rf /var/lib/apt/lists/*

# 새 터미널마다 자동으로 ROS 환경을 읽어오도록 설정
RUN echo 'source /opt/ros/jazzy/setup.bash' >> /home/ubuntu/.bashrc && \
    echo '[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash' >> /home/ubuntu/.bashrc && \
    echo 'export TURTLEBOT3_MODEL=burger' >> /home/ubuntu/.bashrc

# 주의: 이 베이스 이미지의 entrypoint(useradd, /etc/sudoers, supervisord)는 root 권한이 필요하므로
# USER 를 ubuntu 로 바꾸면 안 된다. entrypoint 가 내부적으로 ubuntu 유저 데스크톱을 띄운다.
WORKDIR /home/ubuntu/ros2_ws
