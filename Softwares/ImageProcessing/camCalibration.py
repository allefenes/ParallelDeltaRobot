import numpy as np
import cv2
import glob
import os

def camSavePhotos(imgRequest=50, imgWait=50):
    """

    param imgRequest : How many pictures do you want?
    param imgWait : How many milliseconds should it wait between each image?

    You can take photos into the example file with this function.

    """


    # Create examples folder
    if not os.path.exists('examples'):
        os.makedirs('examples')

    # Create the VideoCapture object (specify the camera number)
    cam = cv2.VideoCapture(1)

    # Image save counter
    imgCounter = 0

    while imgCounter < imgRequest:
        # Take a picture
        ret, frame = cam.read()

        # Show the picture
        cv2.imshow('OpenCV Taking Pictures', frame)

        # save the image in the example folder
        folderName = f'examples/frame{imgCounter}.jpg'
        cv2.imwrite(folderName, frame)

        # Increase save counter
        imgCounter += 1

        # Wait a moment before taking the next frame (user may have turned it off)
        cv2.waitKey(imgWait)

    print(f'{imgCounter} frame saved.')

    # Release the VideoCapture object and close the window
    cam.release()
    cv2.destroyAllWindows()


def camCalibration(xsq = 6, ysq = 6, iter=50, eps=0.01):

    """

    param xsq : X axis dimensions of chesstable
    param ysq : Y axis dimensions of chesstable
    param iter : Iteration criterion
    param eps : Eps criterion

    You can calculate camera matrix and total calculation 
    error with this function. This function uses images in
    the examples file.

    """

    # termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, iter, eps)

    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((ysq*xsq,3), np.float32)
    objp[:,:2] = np.mgrid[0:xsq,0:ysq].T.reshape(-1,2)
    objp[:,:2] *= 20

    # Arrays to store object points and image points from all the images.
    objpoints = [] # 3D point in real world space
    imgpoints = [] # 2D points in image plane.

    images = glob.glob('examples/*.jpg')

    for fname in images:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Find the chess board corners
        ret, corners = cv2.findChessboardCorners(gray, (xsq, ysq), None)

        # If found, add object points, image points (after refining them)
        if ret == True:
            objpoints.append(objp)

            cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            imgpoints.append(corners)

    # Camera calibration
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

    # Print calculated camera matrix
    print("Camera Matrix:")
    print(mtx)

    img = cv2.imread('examples/frame10.jpg')  # You can use the first image as an example
    h,  w = img.shape[:2]
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))

    # undistort
    mapx,mapy = cv2.initUndistortRectifyMap(mtx,dist,None,newcameramtx,(w,h),5)
    dst = cv2.remap(img,mapx,mapy,cv2.INTER_LINEAR)

    #Save calibration result 
    if not os.path.exists('result'):
        os.makedirs('result')

    np.savez(f'result/calResult.npz',mtx=mtx, dist=dist, rvecs=rvecs, tvecs=tvecs)

    # crop the image
    x,y,w,h = roi
    dst = dst[y:y+h, x:x+w]
    cv2.imwrite(f'result/calResult.jpg',dst)

    # Reprojection Error
    mean_error = 0

    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
        mean_error += error

    print( "total error: {}".format(mean_error/len(objpoints)) )

#camSavePhotos(200,50)
camCalibration()