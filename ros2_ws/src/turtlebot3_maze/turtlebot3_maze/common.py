"""노드들이 함께 쓰는 작은 도우미."""
import math

from geometry_msgs.msg import TwistStamped


def make_cmd(node, linear=0.0, angular=0.0):
    """Gazebo TurtleBot3 의 /cmd_vel 은 Twist 가 아니라 TwistStamped 다."""
    msg = TwistStamped()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = 'base_link'
    msg.twist.linear.x = float(linear)
    msg.twist.angular.z = float(angular)
    return msg


def yaw_from_quaternion(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def wrap(a):
    """각도를 -pi ~ pi 로."""
    return math.atan2(math.sin(a), math.cos(a))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))
