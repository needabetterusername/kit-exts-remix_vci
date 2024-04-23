import os
from pathlib import Path

import omni.ext
import omni.ui as ui
from pxr import UsdGeom, Sdf


# Functions and vars are available to other extension as usual in python: `example.python_ext.some_public_function(x)`
# def some_public_function(x: int):
#     print("[codetestdummy.omniverse.kit.remix_vci] some_public_function was called with x: ", x)
#     return x ** x


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class CodetestdummyOmniverseKitRemix_vciExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.

    _FILE_NAME_PREFIX = "E_"
    _CUSTOM_PROP_NAME = "CTD_VCI"

    _flg_verify_ok: bool = False
    _flg_processing: bool = False

    _string_model_search = ui.SimpleStringModel()
    _status_lbl: str = "Please verify before applying."
    _upgd_meshfile_pfx: str = "E_"
    _stage_path = "/RootNode/meshes"
    _capture_layer_path = "/RootNode/meshes"
    _edit_layer_path = "/RootNode/meshes"
    _processable_prim_specs: list = []
    _mesh_files: list = []

    def on_startup(self, ext_id):
        # startup/shutdown print calls from template are causing errors when launcher is not running.
        # print("[codetestdummy.omniverse.kit.remix_vci] codetestdummy omniverse kit remix_vci startup")
        stage = omni.usd.get_context().get_stage()
        layer_stack = stage.GetLayerStack()
        self.__layer_options = [layer.GetDisplayName() for layer in layer_stack]

        self._window = ui.Window("VCI for Remix", width=310, height=400)
        with self._window.frame:
            with ui.VStack():

                ui.Label("Please select capture layer:", height=25)
                self.__combo_box_capture = ui.ComboBox(0, *self.__layer_options, name="dropdown_menu_capture", height=30)
                self.__combo_box_capture.model.add_item_changed_fn(self.on_select_layer)

                ui.Label("Please select edit target layer:", height=25)
                self.__combo_box_edit = ui.ComboBox(0, *self.__layer_options, name="dropdown_menu_edit", height=30)

                ui.Label("Please select replacement meshes folder:", height=25)
                with ui.HStack(height=40):
                    ui.StringField(model=self._string_model_search, enabled=False, height=25)
                    #self._string_model_search.as_string = ""
                    self.val_changed_id = self._string_model_search.subscribe_end_edit_fn(self.on_end_edit_path)
                    ui.Button("Browse", clicked_fn=self.on_browse_path, width=50, height=30)


                def on_verify():
                    self.verify_options()

                def on_apply_overrides():
                    self.add_overrides()

                def on_apply_transforms():
                    pass

                ui.Button("Verify", clicked_fn=on_verify, height=25)

                label = ui.Label("Status:",height=25)
                self._status_lbl = ui.Label("")

                with ui.HStack(height=25):
                    ui.Button("Override References", clicked_fn=on_apply_overrides, height=25)
                    ui.Button("Add Transforms", clicked_fn=on_apply_transforms, height=25, enabled=False)

    def on_select_layer(self, arg1, arg2):
        self._flg_verify_ok = False
        print(type(arg1))
        print(type(arg2))

    def on_browse_path(self):
        # https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/source/extensions/omni.kit.window.filepicker/docs/index.html
        self.__filepicker = omni.kit.window.filepicker.FilePickerDialog("my-filepicker", apply_button_label="Select", click_apply_handler=self.on_click_select)
        self.__filepicker.show()

    def on_click_select(self, file_name, dir_path):
        self._string_model_search.as_string = dir_path
        self.__filepicker.hide()

    def on_end_edit_path(self, item_model):
        self._flg_verify_ok = False
        self._meshes_folder = self._string_model_search.as_string

    def set_status_message(self, status_string: str):
        self._status_lbl.text = status_string

    def verify_options(self):
        report: str = ""
        stage = omni.usd.get_context().get_stage()
        
        self._capture_layer_selection = self.__combo_box_capture.model.get_item_value_model().get_value_as_int()
        self._edit_layer_selection = self.__combo_box_edit.model.get_item_value_model().get_value_as_int()
        self._meshes_path = self._string_model_search.get_value_as_string()

        # if (capture_layer_selection == 0) or (edit_layer_selection == 0):
        #     report = "Error: Select both capture and edit layers."
        #     self.set_status_message(report)
        #     self._flg_verify_ok = False
        # 
        #     return

        if self._capture_layer_selection == self._edit_layer_selection:
            report = "Error: Edit target layer cannot be capture layer."
            self.set_status_message(report)
            self._flg_verify_ok = False

            return
        
        if not self._meshes_path:
            report = "Error: Select replacement meshes folder."
            self.set_status_message(report)
            self._flg_verify_ok = False

            return

        # Get mesh_HASH PrimSpecs from capture layer
        capture_layer = self.get_selected_capture_layer()
        captured_meshes_prim = capture_layer.GetPrimAtPath(self._capture_layer_path)
        if not captured_meshes_prim:
            self._flg_verify_ok = False
            report = f"Error: Could not get capture layer meshes parent at: {self._capture_layer_path}"
            self.set_status_message(report)
            return

        captured_mesh_primspecs = captured_meshes_prim.nameChildren
        report += f"Found {len(captured_mesh_primspecs)} meshes in capture layer.\n"

        # List all files in the directory
        self._mesh_files = self.get_asset_files()
        report += f"Found {len(self._mesh_files)} replacement assets.\n"

        # Get mesh_HASH PrimSpecs from edit target layer
        edit_layer = self.get_selected_edit_layer()
        edit_meshes_prim = edit_layer.GetPrimAtPath(self._edit_layer_path)
        if not edit_meshes_prim:
            self._flg_verify_ok = False
            report += f"Warning: Could not get edit target layer meshes parent at: {self._edit_layer_path}\n"
            self.set_status_message(report)
        else:
            edit_mesh_primspecs = edit_meshes_prim.nameChildren
            report += f"Found {len(edit_mesh_primspecs)} pre-existing overrides in edit layer.\n"

        # Get prims from stage
        stage_prim = stage.GetPrimAtPath(self._stage_path)
        if not stage_prim:
            self._flg_verify_ok = False
            report = f"Error: Could not meshes prim from stage at: {self._stage_path}"
            self.set_status_message(report)
            return

        stage_mesh_prims = stage_prim.GetChildren()
        report += f"Found {len(stage_mesh_prims)} meshes on the stage.\n" 


        self.set_status_message(report)
        self._flg_verify_ok = True

        return

        scope_prim = stage.GetPrimAtPath(path)
        if scope_prim:

            children: list = scope_prim.GetChildren()

            for child_prim in children:
                
                prim_name = child_prim.GetName()
                prim_spec = root_layer.GetPrimAtPath(child_prim.GetPath())
                if prim_spec:
                    # Check the reference edits
                    ref_list = prim_spec.referenceList
                    deleted_items = ref_list.deletedItems
                    prepend_items = ref_list.prependedItems

                    if deleted_items and prepend_items:
                        # Check for matching delete and prepend for "mesh_ABCD" and "E_mesh_ABCD" in assetPath properties
                        # for ref in deleted_items:
                            # if 'visual_correction' in str(ref.primPath):
                            #     self._processable_prim_specs.append(prim_spec)
                        #if any(deleted_item.)
                        pass

            report = f"Found {len(children)} children of which {len(self._processable_prim_specs)} are processable."
            self.set_status_message(report)
            self._flg_verify_ok = True
        else:
            self.set_status_message("Invalid scope path.")
            self._flg_verify_ok = False

    def get_selected_capture_layer(self):
        return omni.usd.get_context().get_stage().GetLayerStack()[self._capture_layer_selection]

    def get_selected_edit_layer(self):
        return omni.usd.get_context().get_stage().GetLayerStack()[self._edit_layer_selection]

    def get_asset_files(self):
        return [file for file in Path(self._meshes_path).iterdir() if file.is_file() and file.name.startswith(self._upgd_meshfile_pfx+"mesh")]

    # For all prims on stage, if there is a similarly named asset file, and not a similary named override
    # override the asset location (in the edit target layer)
    def add_overrides(self):
        if not self._flg_verify_ok:
            self.set_status_message("Please verify before overriding.")
        else:
            report = ""
            # Find applicable targets
            stage = omni.usd.get_context().get_stage()
            edit_layer = self.get_selected_edit_layer()
            stage.SetEditTarget(edit_layer)

            stage_prims = stage.GetPrimAtPath(self._stage_path).GetChildren()
            asset_files = self.get_asset_files()
            asset_file_names = [file.stem[len(self._FILE_NAME_PREFIX):] for file in asset_files]

            edit_meshes_prim = self.get_selected_edit_layer().GetPrimAtPath(self._edit_layer_path)
            overrides = edit_meshes_prim.nameChildren if edit_meshes_prim else []
            override_names = [spec.name for spec in overrides]

            target_stage_prims = [prim for prim in stage_prims if (prim.GetName() in asset_file_names) and (prim.GetName() not in override_names)]
            print(target_stage_prims)

            # Add reference overrides
            for prim in target_stage_prims:
                asset_file = [file for file in asset_files if file.stem[len(self._FILE_NAME_PREFIX):] == prim.GetName()]
                print(asset_files)

                if (asset_files):
                    asset_file_path = asset_file[0]
                    relative_asset_path = os.path.relpath(asset_file_path, start=os.path.dirname(edit_layer.realPath)).replace('\\','/')

                    # Find the original references from the PrimSPec in the Capture Layer
                    capture_layer = self.get_selected_capture_layer()
                    prim_spec = capture_layer.GetPrimAtPath(prim.GetPath())
                    for reference in prim_spec.referenceList.prependedItems:
                        # Resolve reference to absolute path
                        reference_path = os.path.join(os.path.dirname(capture_layer.realPath), reference.assetPath)
                        # Convert absolute path to path relative to edit layer
                        relative_reference_path = os.path.relpath(reference_path, start=os.path.dirname(edit_layer.realPath)).replace('\\','/')
                        prim.GetReferences().RemoveReference(Sdf.Reference(relative_reference_path,reference.primPath))

                    # Add new reference
                    prim.GetReferences().AddReference(Sdf.Reference(relative_asset_path))
                    # Set visibility attribute
                    visibility_attr = UsdGeom.Imageable(prim).CreateVisibilityAttr()
                visibility_attr.Set("inherited")

    def apply_vci(self):
        if not self._flg_verify_ok:
            self.set_status_message("Please verify before applying.")
        else:
            self.set_status_message("Not supported.")
            return
        
            prim_specs = self._processable_prim_specs
            if prim_specs:
                total = len(prim_specs)
                if total:
                    count = 0
                    for prim_spec in prim_specs:
                        try:
                            self.set_status_message(f"Applying VCI to Prim {count+1} of {total}")
                            count += 1
                        except Exception as e:
                            print(f"Exception while processing {prim_spec}: {e}")
                    self.set_status_message(f"DRY RUN: Finished applying to {count} of {total} prims.")
            else:
                self.set_status_message("Nothing to process!")

    def get_xform_from_assetfile(asset_path: str):
        pass

    def apply_xform_override_to_prim(prim_path: str):
        pass

    def on_shutdown(self):
        print("[codetestdummy.omniverse.kit.remix_vci] codetestdummy omniverse kit remix_vci shutdown")
