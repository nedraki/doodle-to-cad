
import sys, numpy as np, cv2
sys.path.insert(0, "/tmp/doodle-brep-67")
img = cv2.imdecode(np.frombuffer(open("/tmp/doodle-brep-67/benchmarks/cases/103_y_motor_holder/source/drawing.png","rb").read(), np.uint8), cv2.IMREAD_COLOR)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)
binary = cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,9)
binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2,2),np.uint8))
contours, hier = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
hz = hier[0]
for i,c in enumerate(contours):
    a=cv2.contourArea(c); p=cv2.arcLength(c,True); circ=4*np.pi*a/(p*p) if p else 0
    x,y,bw,bh=cv2.boundingRect(c)
    kids=[int(j) for j,t in enumerate(hz) if int(t[3])==i]
    ka=[cv2.contourArea(contours[j]) for j in kids]
    print(f"i={i} depth-parent={int(hz[i][3])} area={a:.0f} circ={circ:.3f} bbox=({x},{y},{bw},{bh}) kids={list(zip(kids,[round(k) for k in ka]))}")
