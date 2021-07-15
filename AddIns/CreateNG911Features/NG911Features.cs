using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Windows.Input;
using System.Threading.Tasks;
using ArcGIS.Core.CIM;
using ArcGIS.Core.Data;
using ArcGIS.Core.Geometry;
using ArcGIS.Desktop.Catalog;
using ArcGIS.Desktop.Core;
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
    internal class NG911Features : Module
    {
        private static NG911Features _this = null;
        private const string _addressDockpaneID = "CreateNG911Features_AddressPointDockPane";

        /// <summary>
        /// Retrieve the singleton instance to this module here
        /// </summary>
        public static NG911Features Current
        {
            get
            {
                return _this ?? (_this = (NG911Features)FrameworkApplication.FindModule("CreateNG911Features_Module"));
            }
        }

        private static AddressPointDockPaneViewModel _addressDockPane;
        internal static AddressPointDockPaneViewModel AddressPointVM
        {
            get
            {
                if (_addressDockPane == null)
                {
                    _addressDockPane = FrameworkApplication.DockPaneManager.Find(_addressDockpaneID) as AddressPointDockPaneViewModel;
                }
                return _addressDockPane;
            }
        }

        #region Overrides
        /// <summary>
        /// Called by Framework when ArcGIS Pro is closing
        /// </summary>
        /// <returns>False to prevent Pro from closing, otherwise True</returns>
        protected override bool CanUnload()
        {
            //TODO - add your business logic
            //return false to ~cancel~ Application close
            return true;
        }

        #endregion Overrides

    }
}
