# aruco_opencv
A ROS package for detecting ArUco markers. The difference between this package and [aruco_ros](https://github.com/pal-robotics/aruco_ros) is that it uses the [aruco module](https://docs.opencv.org/4.x/d9/d6a/group__aruco.html) from OpenCV libraries instead of the [original ArUco library](https://www.uco.es/investiga/grupos/ava/node/26).

## Features

- **Runtime Configuration Switching**: Dynamically change ArUco dictionary and marker size without node restart
- Lifecycle node support with automatic or manual activation
- Multiple dictionary support (4x4, 5x5, 6x6, 7x7, AprilTag variants)
- Board detection for improved accuracy
- TF broadcasting and frame transformation
- Comprehensive parameter tuning (25+ ArUco detector parameters)
- Debug visualization with marker axes overlay

