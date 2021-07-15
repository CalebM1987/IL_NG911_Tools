using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using ArcGIS.Core.CIM;
using ArcGIS.Core.Data;
using ArcGIS.Core.Geometry;
using ArcGIS.Desktop.Catalog;
using ArcGIS.Desktop.Core;
using ArcGIS.Desktop.Core.Geoprocessing;
using ArcGIS.Desktop.Editing;
using ArcGIS.Desktop.Extensions;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;
using ArcGIS.Desktop.Framework.Dialogs;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using ArcGIS.Desktop.Layouts;
using ArcGIS.Desktop.Mapping;

namespace CreateNG911Features
{
    internal class CreateGeometry : MapTool
    {
        public CreateGeometry()
        {
            IsSketchTool = true;
            SketchType = SketchGeometryType.Rectangle;
            SketchOutputMode = SketchOutputMode.Map;
        }

        protected override Task OnToolActivateAsync(bool active)
        {
            return base.OnToolActivateAsync(active);
        }

        protected override Task<bool> OnSketchCompleteAsync(Geometry geometry)
        {
            //return base.OnSketchCompleteAsync(geometry);
            var centerlines = (MapView.Active.Map.Layers.First(layer => layer.Name.Equals("RoadCenterline")) as FeatureLayer);
            if (centerlines == null) return Task.FromResult(true);
            Console.WriteLine("Found centerlines");

            return QueuedTask.Run(() =>

            {
                /*
                var spatialFilter = new SpatialQueryFilter()
                {
                    FilterGeometry = geometry,
                    SpatialRelationship = SpatialRelationship.Intersects,
                    SearchOrder = SearchOrder.Spatial
                };
                var queryFilter = new QueryFilter()
                {
                       
                }*/
                //using (Selection closestCenterlines = centerlines.//.Select(spatialFilter)) ;
                MessageBox.Show(String.Format("Geometry type: {0}", geometry.GetType()));
                var searchFeatures = MapView.Active.GetFeatures(geometry);
                MessageBox.Show(String.Format("Selected Features Count: {0}", searchFeatures.Count));

                // find the road centerlines
                var didFindCenterlines = false;
                foreach(KeyValuePair<BasicFeatureLayer, List<long>> entry in searchFeatures)
                {
                    var lyr = entry.Key as FeatureLayer;
                    var dataSource = lyr.GetFeatureClass().GetPath();
                    didFindCenterlines = dataSource.Equals(@"C:\Users\calebma\Documents\IL_911\IL_NG911_Brown_Master_v3.2.5.gdb\Required\RoadCenterline");
                    MessageBox.Show(String.Format("Layer {0} - {1} ({2}) {3}", lyr.Name, dataSource, entry.Value.Count, didFindCenterlines));

                    if (didFindCenterlines)
                    {
                        var oid = lyr.GetTable().GetDefinition().GetObjectIDField();
                        var qf = new QueryFilter()
                        {
                            WhereClause = string.Format("{0} in ({1})", oid, string.Join(",", entry.Value))
                        };
                        lyr.Select(qf);

                        var toolPath = @"C:\Users\calebma\Documents\IL_911\IL_NG911_Tools\Toolbox\NextGen911_Tools.pyt\TestTool";
                        Geoprocessing.OpenToolDialogAsync(toolPath, Geoprocessing.MakeValueArray(dataSource.LocalPath, dataSource.LocalPath));


                        break;
                    }
                }
                return true;
                
                //MapView.Active.SelectFeatures(geometry, SelectionCombinationMethod.New)
            });
        }
    }
}
