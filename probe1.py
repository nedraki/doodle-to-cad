
import sys, numpy as np, cv2
sys.path.insert(0, "/tmp/doodle-brep-67")
img = cv2.imdecode(np.frombuffer(open("/tmp/doodle-brep-67/benchmarks/cases/103_y_motor_holder/source/drawing.png","rb").read(), np.uint8), cv2.IMREAD_COLOR)
h,w = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)
binary = cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,9)
binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2,2),np.uint8))
contours, hier = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
hz = hier[0]
def depth(i):
    d=0;p=int(hz[i][3])
    while p>=0: d+=1;p=int(hz[p][3])
    return d
print("adaptive-threshold pipeline (geometry.py):")
for i,c in enumerate(contours):
    a=cv2.contourArea(c);x,y,bw,bh=cv2.boundingRect(c)
    print(f"i={i} parent={int(hz[i][3])} depth={depth(i)} area={a:.0f} bbox=({x},{y},{bw},{bh})")
# also plain global threshold like evaluation uses
ink = cv2.threshold(gray,190,255,cv2.THRESH_BINARY_INV)[1]
ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
contours2, hier2 = cv2.findContours(ink, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
hz2=hier2[0]
def depth2(i):
    d=0;p=int(hz2[i][3])
    while p>=0: d+=1;p=int(hz2[p][3])
    return d
print("fixed-threshold pipeline (evaluation crops):")
for i,c in enumerate(contours2):
    a=cv2.contourArea(c);x,y,bw,bh=cv2.boundingRect(c)
    print(f"i={i} parent={int(hz2[i][3])} depth={depth2(i)} area={a:.0f} bbox=({x},{y},{bw},{bh})")
