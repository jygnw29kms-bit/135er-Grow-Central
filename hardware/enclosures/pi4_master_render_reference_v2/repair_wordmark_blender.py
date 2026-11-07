import bpy,os
p=r"C:\Users\dezen\Desktop\JL1976\Grow-Central\Pi4-FinalMaster"
src=os.path.join(p,"_05_Embossed_GrowCentral_Wordmark.stl")
dst=os.path.join(p,"P2S_Wordmark_FDM_Repaired.stl")
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
bpy.ops.wm.stl_import(filepath=src)
ob=bpy.context.object
bpy.context.view_layer.objects.active=ob
mod=ob.modifiers.new("Printable_closed_wordmark","REMESH")
mod.mode='VOXEL'
mod.voxel_size=.085
mod.use_smooth_shade=False
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.wm.stl_export(filepath=dst,export_selected_objects=False)
print("REPAIRED",dst,os.stat(dst).st_size)
