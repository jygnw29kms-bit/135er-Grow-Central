$fn = 64;

// Grow Central - Raspberry Pi 4 enclosure
// Units: mm

wall = 2.5;
floor_t = 2.4;
base_h = 28;
lid_t = 3.0;
lip_h = 2.0;
clearance = 0.35;

pcb_l = 85;
pcb_w = 56;
pcb_x = 5.5;
pcb_y = 5.5;

inner_l = 91;
inner_w = 62;
outer_l = inner_l + 2*wall;
outer_w = inner_w + 2*wall;

pi_hole_d = 2.8;
pi_post_d = 6.4;
pi_post_h = 4.5;
pi_holes = [[3.5,3.5],[61.5,3.5],[3.5,52.5],[61.5,52.5]];

case_hole_d = 3.2;
case_post_d = 7.0;
case_posts = [[7.5,7.5],[outer_l-7.5,7.5],[7.5,outer_w-7.5],[outer_l-7.5,outer_w-7.5]];
module rounded_box(size=[10,10,10], r=2) {
    hull() {
        for (x=[r, size[0]-r])
            for (y=[r, size[1]-r])
                translate([x,y,0]) cylinder(r=r,h=size[2]);
    }
}

module rounded_plate_xy(l,w,h,r,z=0,x=0,y=0) {
    translate([x,y,z]) rounded_box([l,w,h],r);
}

// Premium-style tapered enclosure: wider footprint, subtly tighter top edge.
module outer_skin() {
    hull() {
        rounded_plate_xy(outer_l,outer_w,0.8,6.5,0);
        rounded_plate_xy(outer_l-2.4,outer_w-2.4,0.8,5.4,base_h-0.8,1.2,1.2);
    }
}

module shell() {
    difference() {
        outer_skin();
        translate([wall+0.4,wall+0.4,floor_t])
            rounded_box([inner_l-0.8,inner_w-0.8,base_h+1],3.2);
    }
}

module pi_standoffs() {
    for (h=pi_holes) {
        x = wall + pcb_x + h[0];
        y = wall + pcb_y + h[1];
        translate([x,y,floor_t-0.3])
            cylinder(d=pi_post_d,h=pi_post_h+0.3);
    }
}

module pi_standoff_holes() {
    for (h=pi_holes) {
        x = wall + pcb_x + h[0];
        y = wall + pcb_y + h[1];
        translate([x,y,floor_t-0.6])
            cylinder(d=pi_hole_d,h=pi_post_h+1.2);
    }
}
module case_posts_base() {
    for (p=case_posts)
        translate([p[0],p[1],floor_t-0.3])
            cylinder(d=case_post_d,h=base_h-floor_t-0.9);
}

module case_post_holes() {
    for (p=case_posts)
        translate([p[0],p[1],base_h-8.5])
            cylinder(d=2.7,h=9.5);
}

module rounded_port_y(x,z,w,h,r=2,depth=6) {
    hull()
        for (xx=[x+r,x+w-r])
            for (zz=[z+r,z+h-r])
                translate([xx,wall+1.4,zz])
                    rotate([90,0,0]) cylinder(r=r,h=depth);
}

module rounded_port_x(y,z,w,h,r=2,depth=6) {
    hull()
        for (yy=[y+r,y+w-r])
            for (zz=[z+r,z+h-r])
                translate([outer_l-wall-1.4,yy,zz])
                    rotate([0,90,0]) cylinder(r=r,h=depth);
}

module port_cuts() {
    // USB-C power: compact rounded opening.
    rounded_port_y(wall+pcb_x+4.5,6.0,13.0,10.0,2.2);

    // Two separate micro-HDMI openings.
    rounded_port_y(wall+pcb_x+23.0,6.5,10.0,8.5,1.8);
    rounded_port_y(wall+pcb_x+36.0,6.5,10.0,8.5,1.8);

    // 3.5 mm audio jack.
    translate([wall+pcb_x+61.5,wall+1.4,11.5])
        rotate([90,0,0]) cylinder(d=10.0,h=6);

    // Short edge: 2x USB stacks + Ethernet, individually framed.
    rounded_port_x(wall+pcb_y+2.5,6.0,15.0,16.0,2.3);
    rounded_port_x(wall+pcb_y+19.5,6.0,15.0,16.0,2.3);
    rounded_port_x(wall+pcb_y+36.5,6.0,17.0,16.0,2.3);

    // microSD finger access with rounded ends.
    translate([-1.2,wall+pcb_y+19,5.0])
        rotate([0,90,0])
            hull() {
                translate([0,3,0]) cylinder(d=6,h=6);
                translate([0,21,0]) cylinder(d=6,h=6);
            }
}

module strap_ear(y) {
    difference() {
        hull() {
            translate([-1.8,y,0]) rounded_box([5.5,22,6],2.8);
            translate([-11.5,y+2,0]) rounded_box([9,18,6],4.2);
        }
        translate([-8.4,y+5,0.8])
            rounded_box([4.6,12,7],2.2);
    }
}

module strap_ears() {
    strap_ear(9);
    strap_ear(outer_w-31);
}

module base() {
    difference() {
        union() {
            shell();
            pi_standoffs();
            case_posts_base();
            strap_ears();
        }
        port_cuts();
        pi_standoff_holes();
        case_post_holes();
    }
}

lid_x = 1.2;
lid_y = 1.2;
lid_l = outer_l-2.4;
lid_w = outer_w-2.4;
lid_r = 5.4;

module hex_hole(x,y,d=5.6) {
    translate([x,y,-0.3]) cylinder(d=d,h=lid_t+1.8,$fn=6);
}

module lid_vents() {
    // Staggered honeycomb banks left/right of the branding panel.
    for (side=[0,1])
        for (row=[0:3])
            for (col=[0:1]) {
                xx = side==0 ? lid_x+10+col*7 : lid_x+lid_l-10-col*7;
                yy = lid_y+17+row*9+(col%2)*4.5;
                hex_hole(xx,yy,5.4);
            }
}

module lid_gpio_cut() {
    translate([wall+pcb_x+4.5,wall+pcb_y+45,-0.3])
        rounded_box([55,10.5,lid_t+2],2.5);
}

module lid_screw_cuts() {
    for (p=case_posts) {
        translate([p[0],p[1],-0.3])
            cylinder(d=case_hole_d,h=lid_t+2.2);
        translate([p[0],p[1],lid_t-1.1])
            cylinder(d=6.5,h=2.4);
    }
}

module lid_frame() {
    difference() {
        rounded_plate_xy(lid_l,lid_w,0.9,lid_r,lid_t,lid_x,lid_y);
        rounded_plate_xy(lid_l-5.0,lid_w-5.0,1.2,lid_r-2.1,
                         lid_t-0.1,lid_x+2.5,lid_y+2.5);
    }
}

module lid_badge() {
    // Slightly raised center island gives the logo a deliberate home.
    rounded_plate_xy(58,27,0.55,5.6,lid_t,outer_l/2-29,outer_w/2-13.5);
}

module lid_logo() {
    translate([outer_l/2,outer_w/2,lid_t+0.48])
        scale([0.19,0.19,0.008])
            surface(file="grow-central-logo-binary.png",
                    center=true, convexity=10);
}

module lid_body() {
    union() {
        rounded_plate_xy(lid_l,lid_w,lid_t,lid_r,0,lid_x,lid_y);
        lid_frame();
        lid_badge();
    }
}

module lid() {
    union() {
        difference() {
            lid_body();
            lid_screw_cuts();
            lid_gpio_cut();
            lid_vents();
        }
        lid_logo();
    }
}

module pi_reference() {
    color([0,0.55,0.18,0.55])
        translate([wall+pcb_x,wall+pcb_y,floor_t+pi_post_h])
            cube([pcb_l,pcb_w,1.6]);

    // Simplified connector envelopes for visual clearance check.
    color([0.7,0.7,0.7,0.7]) {
        translate([wall+pcb_x+6,wall+pcb_y-2,floor_t+pi_post_h+1.6])
            cube([12,4,8]);
        translate([wall+pcb_x+25,wall+pcb_y-2,floor_t+pi_post_h+1.6])
            cube([29,4,7]);
        translate([wall+pcb_x+59,wall+pcb_y-2,floor_t+pi_post_h+1.6])
            cube([12,4,10]);
        translate([wall+pcb_x+82,wall+pcb_y+5,floor_t+pi_post_h+1.6])
            cube([6,48,15]);
    }
}

part = "preview"; // "base", "lid", "preview"

if (part == "base")
    base();
else if (part == "base_no_ears")
    difference() {
        union() { shell(); pi_standoffs(); case_posts_base(); }
        port_cuts();
        pi_standoff_holes();
        case_post_holes();
    }
else if (part == "shell_only")
    difference() { shell(); port_cuts(); }
else if (part == "shell_pi")
    difference() {
        union() { shell(); pi_standoffs(); }
        port_cuts(); pi_standoff_holes();
    }
else if (part == "shell_case")
    difference() {
        union() { shell(); case_posts_base(); }
        port_cuts(); case_post_holes();
    }
else if (part == "lid")
    lid();
else {
    base();
    pi_reference();
    translate([outer_l+15,0,0]) lid();
}
