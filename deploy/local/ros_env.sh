#!/usr/bin/env bash
# Source after /opt/ros/jazzy/setup.bash on the Linux development machine.
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
# Do not set ROS_LOCALHOST_ONLY: DDS discovery must work across the LAN.
