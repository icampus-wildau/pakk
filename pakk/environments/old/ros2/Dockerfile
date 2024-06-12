# Test Environment for ROS2

FROM ros:humble-ros-base-jammy

# Install and update pip
RUN apt update && apt install -y python3-pip
RUN pip install -U pip
RUN pip install setuptools==58.2.0

ENV PYTHONPATH=/python-packages:$PYTHONPATH

# docker build -t ros2_env .
