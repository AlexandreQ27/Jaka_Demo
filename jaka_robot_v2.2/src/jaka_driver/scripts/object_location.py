#!/usr/bin/python3
import rospy
import cv2
import os
import numpy as np
import pyrealsense2 as rs
import transforms3d as tfs
import math
import yaml
import time
from geometry_msgs.msg import Point
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from jaka_msgs.srv import GetObjPos,GetObjPosResponse
from geometry_msgs.msg import PoseStamped
from geometry_msgs.msg import TwistStamped
data = [0.986025 ,-0.0740463 ,  0.149235  , -118.962,
 -0.152792 , -0.758973 ,  0.632941  , -902.568,
 0.0663988  ,-0.646898 , -0.759681  ,  602.145,
         0 ,         0    ,      0      ,    1
]
#-9.50506
#data = [  0.997115, -0.0552664 ,-0.0520413 ,  25.01485,
# 0.0100422 , -0.583489  , 0.812059,   -931.128,
#-0.0752451 , -0.810238  , -0.58125 ,   462.138,
#         0   ,       0  ,        0    ,      1
#]
camera_matrix=np.array([[617.3667536458366, 0, 321.8601748985215],
 [0, 601.5438424007756, 224.1603617400166],
 [0, 0, 1]])
dist_coeff=np.float32([-0.03319755171620913,
 1.2204467539682,
 0.01235353679874466,
 -0.001081153483005078,
 -4.167413969414598])
 
 # 已经有的相机矩阵和畸变系数  
#camera_matrix = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])  
#dist_coefs = np.array([k1, k2, p1, p2, k3])  
#axis: -0.118479   0.93741  0.327451
bridge = CvBridge()
object_position = Point()
# 定义保存彩色图像和深度图像的目录和文件名  
color_dir = '/home/qyb/jaka_robot_v2.2/data/'  
matrix = np.array(data).reshape((4, 4)) 

# 创建一个相机实例
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
pipeline.start(config)

# 获取深度传感器的内参
profile = pipeline.get_active_profile()
depth_profile = rs.video_stream_profile(profile.get_stream(rs.stream.depth))
depth_intrinsics = depth_profile.get_intrinsics()
print(depth_intrinsics)

ball_color = 'blue'
color_dist = {'red': {'Lower': np.array([0, 60, 60]), 'Upper': np.array([10, 255, 255])},
              'blue': {'Lower': np.array([100, 80, 46]), 'Upper': np.array([124, 255, 255])},
              'green': {'Lower': np.array([35, 50, 50]), 'Upper': np.array([80, 255, 255])},
              }
with open('../../hand_eye_calibration/yaml/camera_to_base_matrix.yaml', 'r') as f:
        cam2base = yaml.load(f.read(), Loader=yaml.FullLoader)
        cam2base = np.array(cam2base)  # The camera-to-base matrix

def object_service_callback(request):
    frames = pipeline.wait_for_frames()

    # 获取彩色图像帧
    color_frame = frames.get_color_frame()
    if not color_frame:
        return

    # 将图像帧转换为OpenCV格式
    distorted_image = np.asanyarray(color_frame.get_data())
    #camera_matrix_umat = cv2.UMat(camera_matrix)
    #dist_coeff_umat = cv2.UMat(dist_coeff)
    color_image = cv2.undistort(distorted_image, camera_matrix, dist_coeff)
    #color_image=distorted_image

    # 对图像进行处理
    gs_frame = cv2.GaussianBlur(color_image, (5, 5), 0)
    hsv = cv2.cvtColor(gs_frame, cv2.COLOR_BGR2HSV)
    erode_hsv = cv2.erode(hsv, None, iterations=2)
    inRange_hsv = cv2.inRange(erode_hsv, color_dist[ball_color]['Lower'], color_dist[ball_color]['Upper'])
    cv2.imshow('inRange_hsv', inRange_hsv)
    # 开操作
    #kernel = np.ones((5, 5), np.uint8)
    #opened_hsv = cv2.morphologyEx(inRange_hsv, cv2.MORPH_OPEN, kernel)
    # 闭操作
    #closed_hsv = cv2.morphologyEx(opened_hsv, cv2.MORPH_CLOSE, kernel)
    #cv2.imshow('closed_hsv', closed_hsv)
    cnts = cv2.findContours(inRange_hsv.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    if len(cnts) > 0:
        c = max(cnts, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        cv2.drawContours(color_image, [np.int0(box)], -1, (0, 255, 255), 2)
        # 计算物体轮廓的中点坐标
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            # 在图像上绘制中点坐标
            cv2.circle(color_image, (cx, cy), 5, (0, 255, 0), -1)
            # 获取深度帧
            depth_frame = frames.get_depth_frame()
            depth_value = depth_frame.get_distance(cx, cy)
            # 将中点坐标转换为相机坐标系下的坐标
            camera_point = pixel_to_camera(cx, cy, depth_value)
            x_eye = camera_point[0]*1000
            y_eye = camera_point[1]*1000
            z_eye = camera_point[2]*1000
            rx=0.0
            ry=0.0
            rz=0.0
            # Obtaining object-to-camera matrix
            global object2cam
            if camera_point is None:
                rospy.logwarn("No object data!")
            else:
                # poses = poses.transforms[0].transform
                # T_object2cam = np.array([[poses.translation.x], [poses.translation.y], [poses.translation.z]])

                # Given rotation angles (rx, ry, rz) in radians
                # Assuming they represent rotations around the x, y, and z axes respectively
                def euler_to_rotation_matrix(rx, ry, rz):
                    Rx = np.array([[1, 0, 0],
                                [0, math.cos(rx), -math.sin(rx)],
                                [0, math.sin(rx), math.cos(rx)]])
                    Ry = np.array([[math.cos(ry), 0, math.sin(ry)],
                                [0, 1, 0],
                                [-math.sin(ry), 0, math.cos(ry)]])
                    Rz = np.array([[math.cos(rz), -math.sin(rz), 0],
                                [math.sin(rz), math.cos(rz), 0],
                                [0, 0, 1]])

                    return np.dot(Rz, np.dot(Ry, Rx))

                # Replace the original quaternion-based rotation with given Euler angles
                rx_rad = math.radians(rx)  # Convert rx from degrees to radians if needed
                ry_rad = math.radians(ry)
                rz_rad = math.radians(rz)
                R_object2cam = euler_to_rotation_matrix(rx_rad, ry_rad, rz_rad)
                # Extract translation vector from poses object
                T_object2cam = np.array([[x_eye],[y_eye],[z_eye]])
                object2cam = np.column_stack((R_object2cam, T_object2cam))
                object2cam = np.row_stack((object2cam, np.array([0, 0, 0, 1])))
                 # Create the rotation matrix from the given Euler angles
                # R = euler_to_rotation_matrix(rx, ry, rz)
            if cam2base is None:
                rospy.logerr("No object_to_camera matrix data!")

            if object2cam is None:
                rospy.logwarn("No object data available!")
                time.sleep(1)

            # Calculating object-to-base matrix
            object2base = np.matmul(cam2base, object2cam)
            R_object2base = object2base[:3, :3]
            T_object2base = object2base[:3, 3]
            rx, ry, rz = tfs.euler.mat2euler(R_object2base)

            pose = TwistStamped()
            pose.twist.linear.x = T_object2base[0]
            pose.twist.linear.y = T_object2base[1]
            pose.twist.linear.z = T_object2base[2]
            pose.twist.angular.x = rx
            pose.twist.angular.y = ry
            pose.twist.angular.z = rz
            #pub.publish(pose)
            rospy.loginfo(f'Object pose: {[T_object2base[0], T_object2base[1], T_object2base[2], rx, ry, rz]}')

            # 发布物体在相机坐标系下的坐标
            
            object_position.x = T_object2base[0]
            object_position.y = T_object2base[1]
            object_position.z = T_object2base[2]
            # print('{}:{}'.format('x', object_position.x))
            # print('{}:{}'.format('y', object_position.y))
            # print('{}:{}'.format('z', object_position.z))
            #object_pub.publish(object_position)
    response=GetObjPosResponse()
    if request.get == True:
        response.x = object_position.x  
        response.y = object_position.y 
        response.z = object_position.z 
        response.message = "{}Get obj pos has been executed".format(object_position.x);
    return response


def pixel_to_camera(pixel_x, pixel_y, depth_value):
    # 将像素坐标转换为相机坐标
    camera_point = rs.rs2_deproject_pixel_to_point(depth_intrinsics, [pixel_x, pixel_y], depth_value)
    return camera_point

def main():
    # 定义保存彩色图像和深度图像的目录和文件名  
    if not os.path.exists(color_dir):  
        os.makedirs(color_dir)  
    # 创建ROS节点和发布器
    # 将数据转换为NumPy数组并塑造为4x4矩阵  
    rospy.init_node('object_detection_node',anonymous=True)
    #rt_data_service = rospy.Service('/jaka_driver/camera_image',Image,rt_data_service_callback)
    object_service = rospy.Service('/get_object_position',GetObjPos,object_service_callback)  
    rate = rospy.Rate(10)
    rospy.spin()


if __name__ == '__main__':
    main()
