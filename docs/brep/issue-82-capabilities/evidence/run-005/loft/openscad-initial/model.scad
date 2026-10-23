$fn=96;
rect_width=40;
n=96; h=50; r=15; d=30;
function q(a)=let(c=cos(a),s=sin(a),v=min((rect_width/2)/max(abs(c),0.000001),(d/2)/max(abs(s),0.000001))) [v*c,v*s,0];
p=concat([for(i=[0:n-1]) q(360*i/n)],[for(i=[0:n-1]) [r*cos(360*i/n),r*sin(360*i/n),h]]);
f=concat([[for(i=[n-1:-1:0]) i]],[[for(i=[0:n-1]) n+i]], [for(i=[0:n-1]) [i,(i+1)%n,n+(i+1)%n,n+i]]);
polyhedron(points=p,faces=f,convexity=10);
