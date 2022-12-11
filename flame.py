import bpy
import numpy as np
from addon_utils import check, enable


class FLAME:

    # Enable addon: flame_tools.
    @staticmethod
    def enable_addon():
        addon = "flame_tools"
        is_enabled, is_loaded = check(addon)
        if not is_enabled:
            print(f"Enable {addon}")
            enable(addon)
            is_enabled, is_loaded = check(addon)
        assert is_enabled and is_loaded, f"'{addon}' is not enabled or loaded!"

    # Get the object.
    @staticmethod
    def get_object():
        # Create the default object.
        object_name = "FLAME-generic"
        bpy.context.window_manager.flame_tool.flame_gender = "generic"
        if object_name not in bpy.data.objects:
            bpy.ops.scene.flame_add_gender()

        # Enable corrective poseshapes.
        bpy.context.window_manager.flame_tool["flame_corrective_poseshapes"] = True

        # Get Object.
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = bpy.data.objects[object_name]
        bpy.data.objects[object_name].select_set(True)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = bpy.data.objects[object_name]
        armature = obj.parent

        # Set rotation mode
        armature.pose.bones["neck"].rotation_mode = 'XYZ'
        armature.pose.bones["jaw"].rotation_mode = 'XYZ'
        armature.pose.bones["left_eye"].rotation_mode = 'XYZ'
        armature.pose.bones["right_eye"].rotation_mode = 'XYZ'
        # Initialize rotation
        armature.pose.bones["neck"].rotation_euler = (0.0, 0.0, 0.0)
        armature.pose.bones["jaw"].rotation_euler = (0.0, 0.0, 0.0)
        armature.pose.bones["left_eye"].rotation_euler = (0.0, 0.0, 0.0)
        armature.pose.bones["right_eye"].rotation_euler = (0.0, 0.0, 0.0)

        # Change range
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape") or key_block.name.startswith("Exp"):
                key_block.slider_min = -10.0
                key_block.slider_max = 10.0
                
        def callback_frame_change_pre(scene, depsgraph):
            armature.pose.bones["neck"].rotation_mode = 'XYZ'
            armature.pose.bones["jaw"].rotation_mode = 'XYZ'
            armature.pose.bones["left_eye"].rotation_mode = 'XYZ'
            armature.pose.bones["right_eye"].rotation_mode = 'XYZ'

        def callback_frame_change_post(scene, depsgraph):
            # print("post frame", obj.data.shape_keys.key_blocks[1].value, armature.pose.bones['jaw'].rotation_euler)
            bpy.data.objects[object_name].select_set(True)
            bpy.ops.object.flame_set_poseshapes('EXEC_DEFAULT')
            bpy.ops.object.flame_update_joint_locations('EXEC_DEFAULT')

        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_pre.append(callback_frame_change_pre)
        bpy.app.handlers.frame_change_post.clear()
        bpy.app.handlers.frame_change_post.append(callback_frame_change_post)

        return obj, armature

    @staticmethod
    def set_animation_fcurves_shapes(obj, num_frames: int, key: str, values: np.ndarray):
        assert key in ["Shape", "Exp"]
        assert values.ndim == 2 and values.shape[0] == num_frames
        frame_range = np.arange(num_frames, dtype="float32")

        # Create the animation action.
        if obj.data.animation_data is None:
            obj.data.animation_data_create()
        if obj.data.animation_data.action is None:
            obj.data.animation_data.action = bpy.data.actions.new("Animation")
        action = obj.data.animation_data.action

        def _set_fcurve(idx: int, val: np.ndarray):
            co = np.stack([frame_range, val], axis=-1)
            # Get f-curve
            fcurve = action.fcurves.find(f"shape_keys.key_blocks[{idx}].value")
            if fcurve is None:
                fcurve = action.fcurves.new(f"shape_keys.key_blocks[{idx}].value")
            # Clear history
            fcurve.keyframe_points.clear()
            # Add frames.
            fcurve.keyframe_points.add(count=num_frames)
            fcurve.keyframe_points.foreach_set("co", co.flatten())

        for idx, key_block in enumerate(obj.data.shape_keys.key_blocks):
            name = key_block.name
            if name.startswith(key):
                vi = int(name[5:]) if key  == "Shape" else int(name[3:])
                vi = vi - 1
                if vi < shp_values.shape[1]:
                    _set_fcurve(idx, values[:, vi])

    @staticmethod
    def set_animation_fcurves_poses(armature, num_frames: int, key: str, values: np.ndarray):
        assert values.ndim == 2 and values.shape[0] == num_frames and values.shape[1] == 3

        # Create animation_data and action.
        if armature.animation_data is None:
            armature.animation_data_create()
        if armature.animation_data.action is None:
            armature.animation_data.action = bpy.data.actions.new("AnimationPoses")
        action = armature.animation_data.action

        # Create curves
        frame_range = np.arange(num_frames, dtype="float32")
        data_path = f'pose.bones["{key}"].rotation_euler'
        for k in range(3):
            co = np.stack([frame_range, values[:, k]], axis=-1)
            fcurve = action.fcurves.find(data_path, index=k)
            if fcurve is None:
                fcurve = action.fcurves.new(data_path, index=k)
            fcurve.keyframe_points.clear()
            fcurve.keyframe_points.add(count=num_frames)
            fcurve.keyframe_points.foreach_set("co", co.flatten())
    
    def __init__(self):
        FLAME.enable_addon()
        self.obj, self.armature = FLAME.get_object()

    def set_animation(self, key: str, values: np.ndarray):
        num_frames = len(values)
        if key in ["Shape", "Exp", "shape", "exp", "shp"]:
            if key == "shp":
                key = "Shape"
            key = key.capitalize()
            FLAME._set_animation_fcurves_shapes(self.obj, num_frames, key, values)
        elif key in ["jaw", "neck", "left_eye", "right_eye"]:
            FLAME._set_animation_fcurves_poses(self.armature, num_frames, key, values)
        else:
            raise ValueError(f"Unknown key: {key}")


if __name__ == "__main__":
    num_frames = 50
    shp_values = np.linspace(-3.0, 3.0, num_frames, dtype="float32")[:, None]
    exp_values = np.linspace(-3.0, 3.0, num_frames, dtype="float32")[:, None]
    jaw_values = np.radians(np.linspace(0.0, 15.0, num_frames, dtype="float32"))[:, None]
    jaw_values = np.broadcast_to(jaw_values, (num_frames, 3))


    flame = FLAME()
    flame.set_animation("shp", shp_values)
    flame.set_animation("exp", shp_values)
    flame.set_animation("jaw", jaw_values)

    scene = bpy.context.scene
    scene.render.fps = 25
    scene.frame_start = 0
    scene.frame_end = num_frames
    scene.frame_current = 0
