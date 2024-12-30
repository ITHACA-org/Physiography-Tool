import arcpy
from arcpy.sa import Con, IsNull
import os
from utils import cems_utils as cems 
arcpy.env.overwriteOutput = True

class physiography_generator:

    def __init__(self):
        self.input_raster = arcpy.GetParameterAsText(0)
        self.field_number = arcpy.GetParameterAsText(1)
        self.fieldnumber_alternative = arcpy.GetParameterAsText(2)
        self.geodatabase = arcpy.GetParameterAsText(3)
        self.buffer_distance = arcpy.GetParameterAsText(4)
        self.contour_lines_interval = arcpy.GetParameterAsText(5)
        self.max_length_threshold = arcpy.GetParameterAsText(6)
        self.temp_gdb = cems.createTempGdb()
        self.dict = {"EU-DEM": 985,
                    "SRTM 90m": 991,
                    "SRTM 30m": 984,
                    "COP-DEM-EEA-10-R": 983,
                    "FABDEM": 981,
                    "None in this list": 997}
        
        # Make attributes that will make objects more handy
        self.aoi_layer = self.permanent_layer("A1_area_of_interest_a")
        self.physiography_layer = self.permanent_layer("D3_physiography_l")
        self.contour_lines = self.temp_layer("contour_lines")
        self.closed_contour_lines = self.temp_layer("ClosedContourLines")
        self.polygon_contour = self.temp_layer("polygon_contour")
        self.clipped_raster = self.temp_layer("clipped_raster")
        self.buffered_AOI = self.temp_layer("buffered_AOI")
        self.crs = self.get_crs()
    
    def temp_layer(self, layer_name: str):
        temp_layer = os.path.join(self.temp_gdb, layer_name)
        return temp_layer
    
    def permanent_layer(self, layer_name: str):
        permanent_layer = os.path.join(self.geodatabase, layer_name)
        return permanent_layer
    
    def get_crs(self):
        crs = cems.getUTMZoneGpd(self.aoi_layer)
        return crs
    
    def manage_raster(self):
        # Clip raster
        arcpy.management.Clip(
        in_raster = self.input_raster,
        rectangle = "#",
        out_raster = self.clipped_raster,
        in_template_dataset = self.buffered_AOI,
        clipping_geometry = "ClippingGeometry",
        maintain_clipping_extent = "NO_MAINTAIN_EXTENT"
        )
        # Set NoData to 0
        desc_obj = arcpy.Describe(self.clipped_raster)
        if isinstance(desc_obj.noDataValue, float):
            out_raster_no_data = Con(IsNull(self.clipped_raster), 0, self.clipped_raster)
            raster_for_geoprocess = arcpy.Raster(out_raster_no_data)
            arcpy.AddMessage("NoData values set to 0 in the clipped raster.")
        elif isinstance(desc_obj.noDataValue, type(None)):
            raster_for_geoprocess = arcpy.Raster(self.clipped_raster)
            arcpy.AddMessage("Raster does not have NoData values.")

        return raster_for_geoprocess
    
    def erasing_algorithm(self):

        # Calculate geometry attributes for erasing algorithm
        arcpy.management.AddFields(
        in_table = self.contour_lines,
        field_description = "x_start DOUBLE # # # #;x_end DOUBLE # # # #;y_start DOUBLE # # # #;y_end DOUBLE # # # #; length_m DOUBLE # # # #",
        template = None
        ) 

        arcpy.management.CalculateGeometryAttributes(
        in_features = self.contour_lines,
        geometry_property = "x_start LINE_START_X;x_end LINE_END_X;y_start LINE_START_Y;y_end LINE_END_Y; length_m LENGTH",
        length_unit="",
        area_unit="",
        coordinate_system = self.crs,
        coordinate_format="SAME_AS_INPUT"
        )

        # Erase features based on length 
        critical_length = float(self.max_length_threshold)
        sql_expression = f"length_m < {critical_length}"
        features_to_delete = arcpy.SelectLayerByAttribute_management(self.contour_lines, "NEW_SELECTION", sql_expression)
        arcpy.management.DeleteFeatures(features_to_delete)

        # Retrieve closed features and calculate their area
        closed_contour_lines = arcpy.SelectLayerByAttribute_management(self.contour_lines, "NEW_SELECTION", "x_start= x_end AND y_start= y_end")
        arcpy.management.CopyFeatures(closed_contour_lines, self.closed_contour_lines)

        arcpy.management.FeatureToPolygon(
        in_features=self.closed_contour_lines,
        out_feature_class=self.polygon_contour,
        cluster_tolerance=None,
        attributes="ATTRIBUTES",
        )

        arcpy.management.AddField(
        in_table=self.polygon_contour,
        field_name="area",
        field_type="DOUBLE",
        field_precision=None,
        field_scale=None,
        field_length=None,
        field_alias="",
        field_is_nullable="NULLABLE",
        field_is_required="NON_REQUIRED",
        field_domain=""
        )

        arcpy.management.CalculateGeometryAttributes(
        in_features=self.polygon_contour,
        geometry_property="area AREA",
        length_unit="",
        area_unit="SQUARE_METERS",
        coordinate_system=self.crs,
        coordinate_format="SAME_AS_INPUT"
        )

        # Erase features based on area

        critical_area = int(self.max_length_threshold)**2
        sql_expression = f"area > {critical_area}"
        features_to_delete = arcpy.SelectLayerByAttribute_management(self.polygon_contour, "NEW_SELECTION", sql_expression)
        arcpy.management.DeleteFeatures(features_to_delete)

        features_to_delete = arcpy.management.SelectLayerByLocation(
        in_layer=self.contour_lines,
        overlap_type="WITHIN",
        select_features=self.polygon_contour,
        search_distance=None,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="NOT_INVERT"
        )

        arcpy.management.DeleteFeatures(features_to_delete)
    
    def or_src_id_code(self):
        return int(self.fieldnumber_alternative) if self.dict[self.field_number] == 997 else self.dict[self.field_number]

    def geoprocessing(self):

        # Buffer the AOI 
        arcpy.analysis.Buffer(
        in_features = self.permanent_layer("A1_area_of_interest_a"),
        out_feature_class = self.temp_layer("buffered_AOI"), 
        buffer_distance_or_field = f"{self.buffer_distance} Meters",
        line_side = "FULL",
        line_end_type = "ROUND",
        dissolve_option = "NONE",
        dissolve_field = None,
        method = "PLANAR"
        )

        # Make contour lines over the clipped raster
        arcpy.ddd.Contour(
        in_raster = self.manage_raster(),
        out_polyline_features = self.contour_lines,
        contour_interval = self.contour_lines_interval,
        base_contour=0,
        z_factor=1,
        contour_type="CONTOUR",
        max_vertices_per_feature=None
        )

        # Erase small features in contour lines
        self.erasing_algorithm()

        # Append data to physiography layer
        arcpy.management.Append(
        inputs = self.contour_lines,
        target= self.physiography_layer,
        schema_type="NO_TEST",
        field_mapping=r'obj_type "Subtype (Element type)" true true false 4 Long 0 0,First,#;name "Name" true true false 255 Text 0 0,First,#;elev "Elevation" true true false 4 Long 0 0,First,#,contour_lines,Contour,-1,-1;notation "Comment" true true false 255 Text 0 0,First,#;or_src_id "Origin Source Identifier" true true false 4 Long 0 0,First,#',
        subtype="CA010-Elevation Contour",
        expression="",
        match_fields=None,
        update_geometry="NOT_UPDATE_GEOMETRY"
        )

        arcpy.management.CalculateField(
        in_table=self.physiography_layer,
        field="or_src_id",
        expression="{}".format(self.or_src_id_code()),
        expression_type="PYTHON3",
        code_block="",
        field_type="TEXT",
        enforce_domains="NO_ENFORCE_DOMAINS"
    )
        
    def RemovePhysiographyOnToc(self):
        aprx = arcpy.mp.ArcGISProject('current')
        map = aprx.listMaps("*")[0]
        for layer in map.listLayers():
            if layer.name == "D3_physiography_l":
                map.removeLayer(layer)
    
    def run(self):
        self.RemovePhysiographyOnToc()
        arcpy.management.DeleteFeatures(in_features = self.physiography_layer)
        self.geoprocessing()
        cems.addLayer(self.physiography_layer)
    
if __name__ == "__main__":
    physiography_generator().run()
