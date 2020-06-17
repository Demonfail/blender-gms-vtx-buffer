bl_info = {
    "name": "Export GameMaker:Studio Vertex Buffer",
    "description": "Exporter for GameMaker:Studio with customizable vertex format",
    "author": "Bart Teunis",
    "version": (1, 0, 1),
    "blender": (2, 82, 0),
    "location": "File > Export",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "https://github.com/blender-to-gmstudio/blender-gms-vbx/wiki",
    "category": "Import-Export"}

if "bpy" in locals():
    import importlib
    if "export_gms_vtx_buffer" in locals():
        importlib.reload(export_gms_vtx_buffer)
    if "conversions" in locals():
        importlib.reload(conversions)

import bpy
import conversions
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    )
from bpy_extras.io_utils import (
    ExportHelper,
    )
from inspect import (
    getmembers,
    isfunction,
    )

gms_vbx_operator_instance = None

class DataPathType(bpy.types.PropertyGroup):
    def items_callback(self, context):
        global gms_vbx_operator_instance
        index = 0
        dp = None
        #gms_vbx_operator_instance = bpy.ops.export_scene.gms_blmod.get_instance()      # Returns a new instance?
        #gms_vbx_operator_instance = ExportGMSVertexBuffer.gms_vbx_operator_instance    # Doesn't work...
        #print("2 - " + str(id(gms_vbx_operator_instance)))
        for attrib in gms_vbx_operator_instance.vertex_format:
            #print(attrib)
            try:
                dp = attrib.datapath
                index = dp.values().index(self)
                break
            except ValueError:
                continue
        if index == 0:
            # Currently supported attribute sources,
            # maintained manually at the moment
            supported_sources = {
                'MeshVertex',
                'MeshLoop',
                'MeshUVLoop',
                'ShapeKeyPoint',
                'VertexGroupElement',
                'Material',
                'MeshLoopColor',
                'MeshPolygon',
                'Scene',
                'Object'
                }
            items = []
            for src in supported_sources:
                rna = getattr(bpy.types,src).bl_rna
                items.append((rna.identifier,rna.name,rna.description))
            return items
        else:
            value = dp[index-1].node
            props = getattr(bpy.types,value).bl_rna.properties
            items = [(p.identifier,p.name,p.description) for p in props]
            return items
    node : bpy.props.EnumProperty(
        name="",
        description="Node",
        items=items_callback,
    )

class VertexAttributeType(bpy.types.PropertyGroup):
    def conversion_list(self, context):
        item_list = []
        item_list.append(("none", "None", "Don't convert the value"))
        item_list.extend([(o[0],o[1].__name__,o[1].__doc__) for o in getmembers(conversions,isfunction)])
        #print(item_list)
        return item_list
    # Actual properties
    datapath : bpy.props.CollectionProperty(name="Path",type=DataPathType)
    fmt : bpy.props.StringProperty(name="Fmt", description="The format string to be used for the binary data", default="fff")
    int : bpy.props.IntProperty(name="Int", description="Interpolation offset, i.e. 0 means value at current frame, 1 means value at next frame", default=0, min=0, max=1)
    func : bpy.props.EnumProperty(name="Func", description="'Pre-processing' function to be called before conversion to binary format", items=conversion_list, update=None)

class ExportGMSVertexBuffer(bpy.types.Operator, ExportHelper):
    """Export (a selection of) the current scene to a vertex buffer, including textures and a description file in JSON format"""
    bl_idname = "export_scene.gms_vtx_buffer"
    bl_label = "Export GM:Studio Vertex Buffer"
    bl_options = {'PRESET'}   # Allow presets of exporter configurations
    
    filename_ext = ".json"
    
    filter_glob : StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    selection_only : BoolProperty(
        name="Selection Only",
        default=True,
        description="Only export objects that are currently selected",
    )
    
    vertex_format : CollectionProperty(
        name="Vertex Format",
        type=VertexAttributeType,
    )
    
    reverse_loop : BoolProperty(
        name="Reverse Loop",
        default=False,
        description="Reverse looping through triangle indices",
    )
    
    frame_option : EnumProperty(
        name="Frame",
        description="Which frames to export",
        items=(('cur',"Current","Export current frame only"),
               ('all',"All","Export all frames in range"),
        )
    )
    
    batch_mode : EnumProperty(
        name="Batch Mode",
        description="How to split individual object data over files",
        items=(('one',"Single File", "Batch all into a single file"),
               ('perobj',"Per Object", "Create a file for each object in the selection"),
               ('perfra',"Per Frame", "Create a file for each frame"),
               ('objfra',"Per Object Then Frame", "Create a directory for each object with a file for each frame"),
               ('fraobj',"Per Frame Then Object", "Create a directory for each frame with a file for each object"),
        )
    )
    
    
    handedness : EnumProperty(
        name="Handedness",
        description="Handedness of the coordinate system to be used",
        items=(('rh',"Right handed",""),
               ('lh',"Left handed",""),
        )
    )
    
    export_mesh_data : BoolProperty(
        name="Export Mesh Data",
        default=False,
        description="Whether to export mesh data to a separate, binary file (.vbx)",
    )
    
    export_json_data : BoolProperty(
        name="Export Object Data",
        default = True,
        description="Whether to export blender data (bpy.data) in JSON format",
    )
    
    object_types_to_export : EnumProperty(
        name="Object Types",
        description="Which types of object data to export",
        options = {'ENUM_FLAG'},
        items=(('cameras',"Cameras","Export cameras"),
               ('lights',"Lights","Export lights"),
               ('speakers',"Speakers","Export speakers"),
               ('armatures',"Armatures","Export armatures"),
               ('materials',"Materials","Export materials"),
               ('textures',"Textures","Export textures"),
               ('actions',"Actions","Export actions"),
               ('curves',"Curves","Export curves"),
               ('collections',"Collections","Export collections"),
        )
    )
    
    export_json_filter : BoolProperty(
        name="Filter Selection",
        default=True,
        description="Whether to filter data in bpy.data based on selection",
    )
    
    apply_transforms : BoolProperty(
        name="Apply Transforms",
        default=True,
        description="Whether to apply object transforms to mesh data",
    )
    
    join_into_active : BoolProperty(
        name="Join Into Active",
        default=False,
        description="Whether to join the selection into the active object",
    )
    
    split_by_material : BoolProperty(
        name="Split By Material",
        default=False,
        description="Whether to split joined mesh by material after joining",
    )
    
    export_textures : BoolProperty(
        name="Export Textures",
        default=True,
        description="Export texture images to same directory as result file",
    )
    
    def invoke(self, context, event):
        #print("operator invoke")
        
        global gms_vbx_operator_instance
        gms_vbx_operator_instance = self
        
        # Blender Python trickery: dynamic addition of an index variable to the class
        bpy.types.Object.batch_index = bpy.props.IntProperty(name="Batch Index")    # Each instance now has a batch index!
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        # TODO: use Panels!
        layout = self.layout
        
        box = layout.box()
        
        box.label(text="General:",icon='SETTINGS')
        
        box.prop(self,property='selection_only')
        box.prop(self,property='frame_option')
        box.prop(self,property='batch_mode')
        
        box = layout.box()
        
        box.label(text="Mesh Data:",icon='MESH_DATA')
        box.prop(self,property="export_mesh_data")
        
        if self.export_mesh_data == True:
            box.label(text="Vertex Format:")
            
            box.operator("export_scene.add_attribute_operator",text="Add")
            
            for index, item in enumerate(self.vertex_format):
                #print(item)
                row = box.row()
                for node in item.datapath:
                    row.prop(node,property='node')
                row.prop(item,property='fmt')
                row.prop(item,property='func')
                row.prop(item,property='int')
                opt_remove = row.operator("export_scene.remove_attribute_operator",text="Remove")
                opt_remove.id = index
        
        box = layout.box()
        
        box.label(text="Object Data:",icon='OBJECT_DATA')
        box.prop(self,property="export_json_data")
        
        if self.export_json_data == True:
            box.prop(self,property="export_json_filter")
            if self.export_json_filter:
                box.prop(self,property="object_types_to_export")
        
        box = layout.box()
        
        box.label(text="Transforms:",icon='CONSTRAINT')
        
        box.prop(self,property="apply_transforms")
        box.prop(self,property='handedness')
        box.prop(self,property='reverse_loop')
        
        box = layout.box()
        
        box.label(text="Extras:",icon='PLUS')
        
        box.prop(self,property='join_into_active')
        box.prop(self,property='split_by_material')
        box.prop(self,property='export_textures')
        
    def cancel(self, context):
        #print("operator cancel")
        
        # Cleanup: remove dynamic property from class
        del bpy.types.Object.batch_index

    def execute(self, context):
        from . import export_gms_vtx_buffer
        return export_gms_vtx_buffer.export(self, context)

# Operators to get the vertex format customization add/remove to work
# See https://blender.stackexchange.com/questions/57545/can-i-make-a-ui-button-that-makes-buttons-in-a-panel
class AddVertexAttributeOperator(bpy.types.Operator):
    """Add a new attribute to the vertex format"""
    bl_idname = "export_scene.add_attribute_operator"
    bl_label = "Add Vertex Attribute"

    def execute(self, context):
        # context.active_operator refers to ExportGMSVertexBuffer instance
        item = context.active_operator.vertex_format.add()
        item.datapath.add()
        item.datapath.add()
        return {'FINISHED'}

class RemoveVertexAttributeOperator(bpy.types.Operator):
    """Remove the selected attribute from the vertex format"""
    bl_idname = "export_scene.remove_attribute_operator"
    bl_label = "Remove Vertex Attribute"
    
    id: bpy.props.IntProperty()
    
    def execute(self, context):
        # context.active_operator refers to ExportGMSVertexBuffer instance
        context.active_operator.vertex_format.remove(self.id)
        return {'FINISHED'}


def menu_func_export(self, context):
    self.layout.operator(ExportGMSVertexBuffer.bl_idname, text="GM:Studio Vertex Buffer (*.json + *.vbx)")


classes = (
    DataPathType,
    VertexAttributeType,
    AddVertexAttributeOperator,
    RemoveVertexAttributeOperator,
    ExportGMSVertexBuffer,
)


def register():
    #print("reg")
    
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    #print("unreg")
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()