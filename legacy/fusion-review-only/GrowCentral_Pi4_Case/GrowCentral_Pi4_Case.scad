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

module shell() {
    difference() {
        rounded_box([outer_l,outer_w,base_h], 3);
        translate([wall,wall,floor_t])
            rounded_box([inner_l,inner_w,base_h], 1.2);
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

module port_cuts() {
    // Power / 2x micro-HDMI / audio side
    translate([wall+pcb_x+5,-1,6]) cube([14,wall+3,11]);
    translate([wall+pcb_x+23,-1,6]) cube([31,wall+3,11]);
    translate([wall+pcb_x+58,-1,6]) cube([14,wall+3,12]);

    // USB / Ethernet end
    translate([outer_l-wall-2,wall+pcb_y+4,6])
        cube([wall+4,52,16]);

    // microSD access
    translate([-1,wall+pcb_y+18,1.2])
        cube([wall+3,28,7.5]);
}

module strap_ears() {
    for (y=[9,outer_w-31]) {
        difference() {
            // 1.2 mm overlap into the enclosure wall = one solid body.
            translate([-8.8,y,0]) rounded_box([10,22,6],3);
            translate([-6.0,y+3.5,1])
                rounded_box([4.8,15,7],2);
        }
    }
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

module lid_vents() {
    for (x=[8,12,16,20,76,80,84,88])
        translate([x,20,-0.2]) cube([2.2,27,lid_t+0.4]);
}

module lid_gpio_cut() {
    translate([wall+pcb_x+4.5,wall+pcb_y+45,-0.2])
        cube([55,10.5,lid_t+0.4]);
}

module lid_screw_cuts() {
    for (p=case_posts) {
        translate([p[0],p[1],-0.2])
            cylinder(d=case_hole_d,h=lid_t+0.4);
        translate([p[0],p[1],lid_t-1.2])
            cylinder(d=6.4,h=1.4);
    }
}

module lid_logo() {
    translate([outer_l/2,outer_w/2,lid_t-0.01])
        scale([0.2,0.2,0.008])
            surface(file="grow-central-logo-binary.png",
                    center=true, convexity=10);
}

module lid() {
    union() {
        difference() {
            rounded_box([outer_l,outer_w,lid_t],3);
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
