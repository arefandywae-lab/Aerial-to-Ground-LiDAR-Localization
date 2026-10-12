#!/usr/bin/env bash
# Ubuntu 24.04 -> ROS2 Jazzy + Gazebo Harmonic (via ros-gz). Run as root.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y curl gnupg lsb-release software-properties-common build-essential git cmake python3-pip python3-venv
add-apt-repository -y universe

curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" > /etc/apt/sources.list.d/ros2.list

apt-get update
apt-get install -y ros-jazzy-ros-base ros-jazzy-ros-gz ros-dev-tools \
  ros-jazzy-pcl-ros ros-jazzy-tf2-ros ros-jazzy-rviz2 libpcl-dev libeigen3-dev mesa-utils

grep -q "ros/jazzy" /root/.bashrc || echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc
echo DONE
