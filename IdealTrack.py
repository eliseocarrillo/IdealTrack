#-------------------------------------------------------------------------------
# Name:        1. Ideal tracks instead of length and gain elevation
# Purpose:     This script calculates gain and loss elevation
#              along a track. The user can choose a sort of track, with a
#              selected gain elevation and a selected length.
#
# Author:      Eliseo Carrillo
#
# Created:     23/02/2016
# Copyright:   (c) Eliseo 2016
# Licence:     <your licence>
#-------------------------------------------------------------------------------
# Import arcpy, os and time modules.
import arcpy
import os
import time

start_time = time.time()

# Workspace and other environments.
wksp = r'Database Connections\SO@DEFAULT@PROYECTO.sde'
arcpy.env.workspace = wksp
arcpy.env.overwriteOutput = True

# Input and output arguments.
    # Input feature classes.
tracks = "Database Connections\SO@DEFAULT@PROYECTO.sde\PROYECTO.DBO.RedViaria\PROYECTO.DBO.Caminos"
startTracks = "Database Connections\SO@DEFAULT@PROYECTO.sde\PROYECTO.DBO.RedViaria\PROYECTO.DBO.InicioCaminos"
    # track Id and start track Id field names.
trackIdField = "NAME"
startTrackIdField = "NAME"
    # Fields names in which the gain and the loss will be stored.
gainField = "DESN_ACUMULADO_POSITIVO"
lossField = "DESN_ACUMULADO_NEGATIVO"
    # Gain elevation range ("Ninguno (camino cuesta abajo)"; "Bajo (0m=<h<50m)";
    # "Medio (50m=<h<100m)"; "Medio-alto  (100m=<h<300m)"; "Alto  (300m=<h)").
gainElevDif = arcpy.GetParameter(0)
    # Fields names in which the shape length is stored.
shapeLengthField = "Shape.STLength()"
    # Length range ("Corta (0km=<longitud<2km)"; "Media (2km=<longitud<5km)";
    # "Larga (5km=<longitud<10km)"; "Muy larga (10km=<longitud)").
length = arcpy.GetParameter(1)
    # Area of interest.
IntArea = arcpy.GetParameter(2)

# Length.
    # Add DBMS-specific field delimiters.
SLFieldDelimited = arcpy.AddFieldDelimiters(arcpy.Describe(tracks).path,
shapeLengthField)

if length == "Corta (0km - 2km)":
    MinLength = 0
    MaxLength = 2000
elif length == "Media (2km - 5km)":
    MinLength = 2000
    MaxLength = 5000
elif length == "Larga (5km - 10km)":
    MinLength = 5000
    MaxLength = 10000
elif length == "Muy larga (>10km)":
    MinLength = 10000
    MaxLength = 100000

# Layers from feature classes inputs.
arcpy.MakeFeatureLayer_management(startTracks, "startTracksLyr")
arcpy.MakeFeatureLayer_management(tracks, "tracksLyr")

# Path selection by area of interest.
in_layer = "startTracksLyr"
overlap_type = "INTERSECT"
select_features = IntArea
arcpy.SelectLayerByLocation_management(in_layer, overlap_type, select_features)

# Relate between Start point paths layer and paths layer.
# Local Variables
OriginTable = "startTracksLyr"
DestinationTable = "tracksLyr"
PrimaryKeyField = startTrackIdField
ForeignKeyField = trackIdField

def buildWhereClauseFromList(OriginTable, PrimaryKeyField, valueList):
  """Takes a list of values and constructs a SQL WHERE
       clause to select those values within a given PrimaryKeyField
       and OriginTable."""

  # Add DBMS-specific field delimiters.
  fieldDelimited = arcpy.AddFieldDelimiters(arcpy.Describe(OriginTable).path,
  PrimaryKeyField)

  # Determine field type.
  fieldType = arcpy.ListFields(OriginTable, PrimaryKeyField)[0].type

  # Add single-quotes for string field values.
  if str(fieldType) == 'String':
    valueList = ["'%s'" % value for value in valueList]

    # Format WHERE clause in the form of an IN statement.
    whereClause = "%s IN(%s)" % (fieldDelimited, ', '.join(map(str, valueList)))
    return whereClause

def selectRelatedRecords(OriginTable, DestinationTable, PrimaryKeyField,
ForeignKeyField):
    """Defines the record selection from the record selection of the OriginTable
      and applys it to the DestinationTable using a SQL WHERE clause built
      in the previous defintion"""

    # Set the SearchCursor to look through the selection of the OriginTable.
    tracksIDs = set([row[0] for row in arcpy.da.SearchCursor(OriginTable,
    PrimaryKeyField)])

    # Establishes the where clause used to select records from DestinationTable.
    whereClause = buildWhereClauseFromList(DestinationTable, ForeignKeyField,
    tracksIDs)

    # Process: Select Layer By Attribute.
    arcpy.SelectLayerByAttribute_management(DestinationTable, "NEW_SELECTION",
    whereClause)

# Process: Select related records between OriginTable and DestinationTable.
selectRelatedRecords(OriginTable, DestinationTable, PrimaryKeyField,
ForeignKeyField)

# Make a new feature layer with selected tracks from tracks feature layer
arcpy.MakeFeatureLayer_management("tracksLyr", "tracksSelectedLyr")

# Selection by length.
SQLMinLength = """{} >= {}""".format(SLFieldDelimited, MinLength)
arcpy.SelectLayerByAttribute_management("tracksSelectedLyr", "NEW_SELECTION",
SQLMinLength)
SQLMaxLength = """{} < {}""".format(SLFieldDelimited, MaxLength)
arcpy.SelectLayerByAttribute_management("tracksSelectedLyr", "SUBSET_SELECTION",
SQLMaxLength)

# Copy selected features to a new feature class.
arcpy.CopyFeatures_management("tracksSelectedLyr", "in_memory/tracksIntAreaNoZ")

# Interpolate shape tool.
in_surface = "Database Connections\SO@DEFAULT@PROYECTO.sde\PROYECTO.DBO.MDT25"
in_feature_class = "in_memory/tracksIntAreaNoZ"
out_feature_class = "in_memory/tracksIntArea"
arcpy.InterpolateShape_3d(in_surface, in_feature_class, out_feature_class)

# Add gain and loss elevation fields if it is necessary
    # Source feature layer
source = "in_memory/tracksIntArea"

needGain = True
needLoss = True
    # Check to see if gain and loss fields already exist.
fields = arcpy.ListFields(source)
for field in fields:
	if field.name == gainField:
		needGain = False
	elif field.name == lossField:
		needLoss = False

    # Add gain and loss fields if they weren't found (to store the results)
if needGain:
    arcpy.AddField_management(source, gainField, "DOUBLE")
    arcpy.AddMessage("Gain Field Added")
else:
	arcpy.AddMessage("Gain Field Already Exists....Editing")
if needLoss:
    arcpy.AddField_management(source, lossField, "DOUBLE")
    arcpy.AddMessage("Loss Field Added")
else:
	arcpy.AddMessage("Loss Field Already Exists....Editing")

# Vertical gain along the path.
    # Add DBMS-specific field delimiters.
gainFieldDelimited = arcpy.AddFieldDelimiters(arcpy.Describe(source).path,
gainField)
lossFieldDelimited = arcpy.AddFieldDelimiters(arcpy.Describe(source).path,
lossField)

if gainElevDif == "Ninguno (camino cuesta abajo)":
    MaxGainElev = 0
    MinLossElev = 0
    MaxLossElev = 10000
elif gainElevDif == "Bajo (0m - 50m)":
    MinGainElev = 0
    MaxGainElev = 50
elif gainElevDif == "Medio (50m - 100m)":
    MinGainElev = 50
    MaxGainElev = 100
elif gainElevDif == "Medio-alto  (100m - 300m)":
    MinGainElev = 100
    MaxGainElev = 300
elif gainElevDif == "Alto  (>300m)":
    MinGainElev = 300
    MaxGainElev = 100000

# Identify the Geometry field.
desc = arcpy.Describe("in_memory/tracksIntArea")
shapeField = desc.ShapeFieldName

# Generate an update cursor for "in_memory/tracksIntArea".
rows = arcpy.UpdateCursor("in_memory/tracksIntArea")
row = rows.next()
rowCount = 0

# Process all records
while row:
	# Get the geometry object
	shp = row.getValue(shapeField)
	partCount = shp.partCount

	# Reset variables for each row
	counter = 0
	gainVal = 0
	lossVal = 0
	avgVal = 0
	lastZ = None
	# Handle multipart objects
	while counter < partCount:
		# Get the point array
		pointArray = shp.getPart(counter)
		pointArray.reset
		pnt = pointArray.next()
		# For every point/node in the object, compare the Z and
		# add differences to the appropriate gain/loss value.
		while pnt:
			if lastZ == None:
				lastZ = pnt.Z
			elif pnt.Z > lastZ:
				gainVal = (pnt.Z - lastZ)
			elif pnt.Z < lastZ:
				lossVal = (lastZ - pnt.Z)
			pnt = pointArray.next()
			# Handle null point separators in the point array
			if pnt == None:
				pnt = pointArray.next()
		counter = counter + 1

	# Insert the gain/loss value to the rows
	row.setValue(gainField, gainVal)
	row.setValue(lossField, lossVal)
	rows.updateRow(row)

	# Print a progress report comment
	rowCount = rowCount + 1
	arcpy.AddMessage(str(rowCount) + ' tracks processed.')
	row = rows.next()

# Feature layer from selected path.
arcpy.MakeFeatureLayer_management("in_memory/tracksIntArea", "tracksIntAreaLyr")

# Path selection by elevation gain.
if MaxGainElev == 0:
    SQLMaxGainElev = """{} = {}""".format(gainFieldDelimited, MaxGainElev)
    arcpy.SelectLayerByAttribute_management("tracksIntAreaLyr", "NEW_SELECTION",
    SQLMaxGainElev)
    SQLMinLossElev = """{} >= {}""".format(lossFieldDelimited, MinLossElev)
    arcpy.SelectLayerByAttribute_management("tracksIntAreaLyr", "SUBSET_SELECTION",
    SQLMinLossElev)
    SQLMaxLossElev = """{} < {}""".format(lossFieldDelimited, MaxLossElev)
    arcpy.SelectLayerByAttribute_management("tracksIntAreaLyr", "SUBSET_SELECTION",
    SQLMaxLossElev)
else:
    SQLMinGainElev = """{} >= {}""".format(gainFieldDelimited, MinGainElev)
    arcpy.SelectLayerByAttribute_management("tracksIntAreaLyr", "NEW_SELECTION",
    SQLMinGainElev)
    SQLMaxGainElev = """{} < {}""".format(gainFieldDelimited, MaxGainElev)
    arcpy.SelectLayerByAttribute_management("tracksIntAreaLyr", "SUBSET_SELECTION",
    SQLMaxGainElev)

# Selection copy into a new feature class.
outputFC = "in_memory/ResultDesnivelAcum"
arcpy.CopyFeatures_management("tracksIntAreaLyr", outputFC)

# Final output as parameter
arcpy.SetParameter(3, outputFC)

# Completion Statement
arcpy.AddMessage("--- %s seconds ---" % (time.time() - start_time))
arcpy.AddMessage("Process Complete")