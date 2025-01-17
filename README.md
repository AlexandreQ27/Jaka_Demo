# Jaka_Robotics_Transformer_Demo
This is a grasping project based on jaka robotic arm. We use ROS1 and OpenCV(HSV or GRCNN) to grasp (eye out of hand).The project includes calculating hand-eye matrices, object recognition, and grasping codes include rt-x test and rt-1 train.


<img src="grasp.png" alt="jaka">
<img src="rt-x.png" alt="rt-x">

## 实验思路
### 1.使用传统抓取方法或者手动操作方法获得抓取数据(finished)

### 2.使用robotics-transformer进行自定义数据集训练（finished）

### 3.使用robotics-transformer训练模型进行抓取（finished）

### 4.使用llama微调输出指令，对robotics-transformer进行控制(not included here)

## General visual grasp(传统方法抓取，并储存训练需要的数据)(HSV or GRCNN)
### 1.Create a ros workspace
Create workspace：
```bash
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
catkin_init_workspace
```
Compile workspace：
```bash
cd ~/catkin_ws/
catkin_make
```
Set environment variables：
```bash
 echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
```
Make the above configuration take effect on the current terminal：
```bash
source ~/.bashrc
```
### 3.Perform your own hand-eye calibration（进行自己的手眼标定）
#### Input
- image with chessboard
- robot pose in txt file (xyz(mm),rpy(deg))

#### Output
- camera intrinsic parameters
- eye hand transformations
  
more detail: https://github.com/ZiqiChai/simplified_eye_hand_calibration

### 4.Run
```bash
   roslaunch jaka_driver my_demo.launch
```

## Use a robotics transformer pre-trained model for inference（使用RT-X预训练模型进行推理）（RT-X pre-trained model）
### 1.Run

**CLICK** [here](https://github.com/AlexandreQ27/RT-X-Demo/tree/91c4622712b1ece0cc3290fcbb3f9d1481460da6) to see the step

## Train your own RT-1 model（使用自定义的数据集训练模型）
```bash
   cd RT-1
   python -m robotics_transformer.single_train_demo
```

## Acknowledgement
reference code: https://github.com/ZiqiChai/simplified_eye_hand_calibration
