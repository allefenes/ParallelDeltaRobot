import cv2
import numpy as np
import glob


def poseEstimation(xsq = 6, ysq = 6, iter=50, eps=0.001):

    # Load previously saved data
    with np.load('result/calResult.npz') as X:
        mtx, dist, _, _ = [X[i] for i in ('mtx','dist','rvecs','tvecs')]

    def draw(img, corners, imgpts):
        corner = tuple(map(int, corners[0].ravel()))
        img = cv2.line(img, corner, tuple(map(int, imgpts[0].ravel())), (255,0,0), 2)
        img = cv2.line(img, corner, tuple(map(int, imgpts[1].ravel())), (0,255,0), 2)
        img = cv2.line(img, corner, tuple(map(int, imgpts[2].ravel())), (0,0,255), 2)
        return img


    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, iter, eps)
    objp = np.zeros((ysq*xsq,3), np.float32)
    objp[:,:2] = np.mgrid[0:xsq,0:ysq].T.reshape(-1,2)
    objp[:,:2] *=20

    axis = np.float32([[20,0,0], [0,20,0], [0,0,-20]]).reshape(-1,3)

    for fname in glob.glob('examples/*.jpg'):
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, (xsq,ysq),None)

        if ret == True:
            corners2 = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)

            # Find the rotation and translation vectors.
            retval, rvecs, tvecs, inliers = cv2.solvePnPRansac(objp, corners2, mtx, dist)


            # project 3D points to image plane
            imgpts, jac = cv2.projectPoints(axis, rvecs, tvecs, mtx, dist)

            img = draw(img,corners2,imgpts)
            cv2.imshow('RESULT',img)
            k = cv2.waitKey(0) & 0xff
            if k == 's':
                cv2.imwrite(fname[:6]+'.png', img)

    cv2.destroyAllWindows()

poseEstimation()