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
    _string_model = ui.SimpleStringModel()
    _meshes_scope = None
    _status_lbl = "Please verify before applying."
    _upgd_meshfile_pfx = "E_"
    _processable_prim_specs = []

    def on_startup(self, ext_id):
        print("[codetestdummy.omniverse.kit.remix_vci] codetestdummy omniverse kit remix_vci startup")

        self._window = ui.Window("VCI for Remix", width=300, height=300)
        with self._window.frame:
            with ui.VStack():

                ui.Label("Please enter path to meshes scope prim:", height=25)
                ui.StringField(model=self._string_model, width=250, height=25)
                self._string_model.as_string = "/RootNode/meshes"
                self.val_changed_id = self._string_model.subscribe_end_edit_fn(self.on_end_edit_path)
                self._meshes_scope = self._string_model.as_string

                def on_verify():
                    self.verify_mesh_scope(self._meshes_scope)

                def on_apply_vci():
                    self.apply_vci()

                ui.Button("Verify", clicked_fn=on_verify, height=25)

                label = ui.Label("Status:",height=25)
                self._status_lbl = ui.Label("")

                ui.Button("Apply VCI", clicked_fn=on_apply_vci, height=25)

    def on_end_edit_path(self, item_model):
        self._flg_verify_ok = False
        self._meshes_scope = self._string_model.as_string
        self.set_status_message("Scope path has changed, please verify.")

    def set_status_message(self, status_string: str):
        self._status_lbl.text = status_string

    def verify_mesh_scope(self, path):

        if not self._flg_verify_ok:
            stage = omni.usd.get_context().get_stage()
            scope_prim = stage.GetPrimAtPath(path)
            root_layer = stage.GetRootLayer()

            if scope_prim:
                report: str = ""
                children: list = scope_prim.GetChildren()

                for child_prim in children:
                    prim_spec = root_layer.GetPrimAtPath(child_prim.GetPath())
                    
                    if prim_spec:
                        # Check the reference edits
                        ref_list = prim_spec.referenceList
                        deleted_items = ref_list.deletedItems
                        prepend_items = ref_list.prependedItems

                        if deleted_items and prepend_items:
                        
                            # Check for visual_correction
                            # Also check that there is a matching prepended "E_mesh_ABCD" assetPath 
                            # when there is a deleted "mesh_ABCD"
                            for ref in deleted_items:
                                if 'visual_correction' in str(ref.primPath):
                                    self._processable_prim_specs.append(prim_spec)

                report = f"Found {len(children)} children of which {len(self._processable_prim_specs)} are processable."
                self.set_status_message(report)
                self._flg_verify_ok = True
            else:
                self.set_status_message("Invalid scope path.")
                self._flg_verify_ok = False
    
    def apply_vci(self):
        if not self._flg_verify_ok:
            self.set_status_message("Please verify before applying.")
        else:
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
