"""
Blender 自动化电气设备生成与导出脚本
使用方法：
1. 打开 Blender (4.0+ / 3.6+)
2. 切换到顶部的 "Scripting" (脚本编写) 工作区
3. 点击 "New" (新建) 并将本脚本内容粘贴进去
4. 点击 "Run Script" (运行脚本)
脚本将自动在场景中建立 220kV 变压器、GIS断路器与架构，并自动在桌面导出 `substation_blender.glb`！
"""

import bpy
import math
import os

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_material(name, color, metallic=0.5, roughness=0.4):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def build_substation():
    clear_scene()

    # 材质
    mat_tank = create_material("Mat_TankSteel", (0.24, 0.29, 0.36, 1.0), metallic=0.6, roughness=0.35)
    mat_copper = create_material("Mat_Copper", (0.72, 0.43, 0.16, 1.0), metallic=0.8, roughness=0.3)
    mat_bushing = create_material("Mat_Porcelain", (0.43, 0.15, 0.12, 1.0), metallic=0.1, roughness=0.2)
    mat_gis = create_material("Mat_GISMetal", (0.51, 0.57, 0.65, 1.0), metallic=0.85, roughness=0.3)

    # 1. 主变压器本体 (trans-1)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-10, 0, 3))
    tank = bpy.context.active_object
    tank.name = "trans-1"
    tank.scale = (8.0, 5.0, 6.0)
    tank.data.materials.append(mat_tank)

    # 变压器储油柜/油枕
    bpy.ops.mesh.primitive_cylinder_add(radius=1.2, depth=7.0, location=(-10, -2.5, 7.5))
    conservator = bpy.context.active_object
    conservator.name = "Conservator_trans-1"
    conservator.rotation_euler = (0, math.pi/2, 0)
    conservator.data.materials.append(mat_tank)

    # 220kV 高压绝缘套管 (3相)
    for i, x_offset in enumerate([-12.5, -10.0, -7.5]):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=3.8, location=(x_offset, 1.2, 7.5))
        bushing = bpy.context.active_object
        bushing.name = f"Bushing_HV_{chr(65+i)}"
        bushing.data.materials.append(mat_bushing)

    # 2. 220kV GIS 组合电器 (gis-201)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.9, depth=6.5, location=(10, 0, 2.5))
    gis_tank = bpy.context.active_object
    gis_tank.name = "gis-201"
    gis_tank.rotation_euler = (0, math.pi/2, 0)
    gis_tank.data.materials.append(mat_gis)

    # GIS 机构箱
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(10, 1.6, 1.2))
    cubicle = bpy.context.active_object
    cubicle.name = "GIS_Cubicle_201"
    cubicle.scale = (1.8, 1.2, 2.2)
    cubicle.data.materials.append(mat_tank)

    # 导出 GLB
    desktop_path = os.path.expanduser("~/Desktop")
    export_filepath = os.path.join(desktop_path, "substation_blender.glb")

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=export_filepath,
        export_format='GLB',
        use_selection=True,
        export_yup=True,
        export_materials='EXPORT',
        export_animations=True
    )
    print(f"变电站模型已成功导出到桌面: {export_filepath}")

if __name__ == "__main__":
    build_substation()
