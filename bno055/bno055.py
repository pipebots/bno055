#!/usr/bin/env python3

# TODO what to do with this original license hint, as the original file has been split... extract to license txt file?
#####################################################################
# Software License Agreement (BSD License)
#
# Copyright (c) 2016, Michal Drwiega
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#####################################################################

import rclpy
from rclpy.node import Node

import threading

from bno055.connectors.uart import UART
from bno055.connectors.i2c import I2C
from bno055.params.NodeParameters import NodeParameters
from bno055.sensor.SensorService import SensorService


class Bno055Node(Node):
    """ROS2 Node for interfacing Bosch Bno055 IMU sensor"""

    sensor = None
    param = None

    def __init__(self):
        # Initialize parent (ROS Node)
        super().__init__('bno055')

    def setup(self):
        # Initialize ROS2 Node Parameters:
        self.param = NodeParameters(self)

        # Get connector according to configured sensor connection type:
        if self.param.connection_type.value == UART.CONNECTIONTYPE_UART:
            connector = UART(self, self.param.uart_baudrate.value, self.param.uart_port.value, self.param.uart_timeout.value)
        elif self.param.connection_type.value == I2C.CONNECTIONTYPE_I2C:
            # TODO implement IC2 integration
            raise NotImplementedError('I2C not yet implemented')
        else:
            raise NotImplementedError('Unsupported connection type: ' + str(self.param.connection_type.value))

        # Connect to BNO055 device:
        connector.connect()

        # Instantiate the sensor Service API:
        self.sensor = SensorService(self, connector, self.param)

        # configure imu
        self.sensor.configure()


def main(args=None):
    """Main entry method for this ROS2 node"""
    # Initialize ROS Client Libraries (RCL) for Python:
    rclpy.init()

    # Create & initialize ROS2 node:
    node = Bno055Node()
    node.setup()

    # Create lock object to prevent overlapping data queries
    lock = threading.Lock()

    # start regular sensor transmissions:
    def read_data():
        """Callback for periodic timer executions in order to retrieve sensor IMU data"""
        if lock.locked():
            # critical area still locked - that means that the previous data query is still being processed
            node.get_logger().warn("Previous data query not yet finished - skipping query cycle")
            return

        # Acquire lock before entering critical area in order to prevent overlapping data queries
        lock.acquire()
        try:
            # perform synchronized block:
            node.sensor.get_sensor_data()
        finally:
            lock.release()

    # please be aware that frequencies around 30Hz and above might cause performance impacts:
    # https://github.com/ros2/rclpy/issues/520
    f = 1.0 / float(node.param.data_query_frequency.value)
    timer = node.create_timer(f, read_data)

    rclpy.spin(node)

    # clean shutdown
    node.destroy_timer(timer)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()