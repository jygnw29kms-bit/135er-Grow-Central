// 135er Grow Central - Raspberry Pi 4 FDM case
// Units: mm
// Designed for FDM printing, 0.4 mm nozzle / 0.2 mm layer.
// Board reference: Raspberry Pi 4 Model B 85 x 56 mm, 58 x 49 mm mounting pattern.

$fn = 48;
PART = "bottom"; // bottom | lid | printplate | assembly

wall = 2.4;
floor_t = 2.4;
lid_t = 2.6;
clearance = 0.7;
board_x = 85;
board_y = 56;
inner_x = board_x + 2*clearance + 2.0;
inner_y = board_y + 2*clearance + 2.0;
base_h = 25.0;
corner_r = 4.0;

pcb_hole_d = 2.75;
pcb_screw_clearance = 2.9;
standoff_d = 6.5;
standoff_h = 3.4;
pcb_hole_x = [3.5, 61.5];
pcb_hole_y = [3.5, 52.5];

lid_screw_d = 3.2;
lid_post_d = 7.5;
lid_post_offset = 5.8;

zip_slot_w = 6.2;
zip_slot_h = 3.0;
zip_ear_depth = 10.0;
zip_ear_thick = 5.0;

outer_x = inner_x + 2*wall;
outer_y = inner_y + 2*wall;

module rounded_box(size=[10,10,10], r=2){
    hull(){
        for (x=[r,size[0]-r]) for (y=[r,size[1]-r])
            translate([x,y,0]) cylinder(r=r,h=size[2]);
    }
}

module rounded_plate(size=[10,10,2], r=2){ rounded_box(size,r); }

module hexvent_field(x0, y0, nx, ny, pitch=8, d=5.0, h=5){
    for (iy=[0:ny-1])
        for (ix=[0:nx-1]) {
            xx = x0 + ix*pitch + (iy%2)*pitch/2;
            yy = y0 + iy*(pitch*0.86);
            translate([xx,yy,-0.5]) cylinder(d=d,h=h,$fn=6);
        }
}

module lid_post(x,y){
    difference(){
        translate([x,y,floor_t]) cylinder(d=lid_post_d,h=base_h-floor_t-1.2);
        translate([x,y,floor_t-0.2]) cylinder(d=2.6,h=base_h-floor_t+1.0);
    }
}

module pcb_standoff(x,y){
    difference(){
        translate([wall+clearance+1.0+x, wall+clearance+1.0+y, floor_t]) cylinder(d=standoff_d,h=standoff_h);
        translate([wall+clearance+1.0+x, wall+clearance+1.0+y, floor_t-0.2]) cylinder(d=pcb_screw_clearance,h=standoff_h+0.6);
    }
}

module cable_tie_ear(xc){
    difference(){
        hull(){
            translate([xc-7, outer_y-1, 0]) cube([14,zip_ear_depth+1,zip_ear_thick]);
            translate([xc-5.5, outer_y+zip_ear_depth-1, 0]) cube([11,1,zip_ear_thick]);
        }
        translate([xc-zip_slot_w/2, outer_y+2.0, -0.2])
            cube([zip_slot_w, zip_ear_depth-2.0, zip_slot_h+0.4]);
    }
}

module side_zip_ear(yc){
    difference(){
        hull(){
            translate([-zip_ear_depth, yc-7, 0]) cube([zip_ear_depth+1,14,zip_ear_thick]);
            translate([-zip_ear_depth, yc-5.5, 0]) cube([1,11,zip_ear_thick]);
        }
        translate([-zip_ear_depth+1.3, yc-zip_slot_w/2, -0.2])
            cube([zip_ear_depth-2.6, zip_slot_w, zip_slot_h+0.4]);
    }
}

module case_bottom(){
    difference(){
        union(){
            rounded_box([outer_x,outer_y,base_h],corner_r);
            cable_tie_ear(outer_x*0.28);
            cable_tie_ear(outer_x*0.72);
            side_zip_ear(outer_y*0.30);
            side_zip_ear(outer_y*0.70);
        }

        translate([wall,wall,floor_t])
            rounded_box([inner_x,inner_y,base_h+1],max(1.5,corner_r-wall));

        translate([outer_x-wall-0.5, wall+4.5, floor_t+standoff_h+0.7])
            cube([wall+1.5, inner_y-9.0, 18.0]);

        translate([wall+clearance+1.0+4.5, -0.5, floor_t+standoff_h+1.4])
            cube([11.5,wall+1.5,7.0]);
        translate([wall+clearance+1.0+19.5, -0.5, floor_t+standoff_h+1.0])
            cube([10.5,wall+1.5,7.5]);
        translate([wall+clearance+1.0+33.5, -0.5, floor_t+standoff_h+1.0])
            cube([10.5,wall+1.5,7.5]);
        translate([wall+clearance+1.0+50.0, -0.5, floor_t+standoff_h+4.4])
            rotate([90,0,0]) cylinder(d=8.2,h=wall+1.5);

        translate([-0.5, wall+inner_y/2-8.5, 0.8])
            cube([wall+1.5,17,6.0]);

        for (i=[0:7])
            translate([17+i*8.0, outer_y-0.6, 8.2]) cube([4.0,wall+1.2,9.0]);

        for (i=[0:5])
            translate([19+i*11,18,-0.2]) cube([5.5,24,floor_t+0.5]);
    }

    for (x=pcb_hole_x) for (y=pcb_hole_y) pcb_standoff(x,y);

    lid_post(lid_post_offset,lid_post_offset);
    lid_post(outer_x-lid_post_offset,lid_post_offset);
    lid_post(lid_post_offset,outer_y-lid_post_offset);
    lid_post(outer_x-lid_post_offset,outer_y-lid_post_offset);

    translate([outer_x*0.60,0.01,17.8]) rotate([90,0,0])
        linear_extrude(height=0.7) text("135er GC",size=4.2,font="Liberation Sans:style=Bold",halign="center");
}

module case_lid(){
    lip_h=2.0;
    lip_t=1.4;
    difference(){
        union(){
            rounded_plate([outer_x,outer_y,lid_t],corner_r);
            translate([wall+0.35,wall+0.35,-lip_h])
                difference(){
                    rounded_box([inner_x-0.7,inner_y-0.7,lip_h],max(1.3,corner_r-wall));
                    translate([lip_t,lip_t,-0.2])
                        rounded_box([inner_x-0.7-2*lip_t,inner_y-0.7-2*lip_t,lip_h+0.4],1.0);
                }
        }

        for (x=[lid_post_offset,outer_x-lid_post_offset])
            for (y=[lid_post_offset,outer_y-lid_post_offset])
                translate([x,y,-0.5]) cylinder(d=lid_screw_d,h=lid_t+1.0);

        for (x=[lid_post_offset,outer_x-lid_post_offset])
            for (y=[lid_post_offset,outer_y-lid_post_offset])
                translate([x,y,lid_t-1.25]) cylinder(d=6.2,h=1.8);

        hexvent_field(24,18,8,4,8.0,5.2,lid_t+1.0);
    }

    translate([outer_x/2,8.7,lid_t])
        linear_extrude(height=0.7)
            text("135er",size=8.4,font="Liberation Sans:style=Bold",halign="center");
    translate([outer_x/2,3.4,lid_t])
        linear_extrude(height=0.65)
            text("GROW CENTRAL",size=3.2,font="Liberation Sans:style=Bold",halign="center");
}

module assembly(){
    color("#202124") case_bottom();
    translate([0,0,base_h+8]) color("#303236") case_lid();
}

if (PART=="bottom") case_bottom();
else if (PART=="lid") case_lid();
else if (PART=="printplate") { case_bottom(); translate([115,0,0]) case_lid(); }
else assembly();
