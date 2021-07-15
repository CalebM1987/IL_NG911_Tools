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
using ArcGIS.Desktop.Editing;
using ArcGIS.Desktop.Extensions;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;
using ArcGIS.Desktop.Framework.Dialogs;
using ArcGIS.Desktop.Framework.Events;
using ArcGIS.Desktop.Mapping.Events;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using ArcGIS.Desktop.Layouts;
using ArcGIS.Desktop.Mapping;
using System.Windows.Input;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Windows;

namespace CreateNG911Features
{
    internal class AddressPointDockPaneViewModel : DockPane
    {
        private const string _dockPaneID = "CreateNG911Features_AddressPointDockPane";
        private const string _selectToolID = "CreateNG911Features_CreateGeometry";//"CreateNG911Features_FeatureSelectionTool";
        Dictionary<Map, SelectedLayerInfo> _selectedLayerInfos = new Dictionary<Map, SelectedLayerInfo>();

        protected AddressPointDockPaneViewModel() {
            Steps = new ObservableCollection<string>();
            Steps.Add("Select Centerline");
            Steps.Add("Draw Point");
            Steps.Add("Address Info");

        }

        #region Step Progressor
        private int m_progress = 33;
        public int Progress
        {
            get { return m_progress; }
            set
            {
                m_progress = value;
                OnPropertyChanged("Progress");
            }
        }

        public ObservableCollection<string> Steps
        {
            get;
            set;
        }

        public event PropertyChangedEventHandler PropertyChanged;
        private void OnPropertyChanged(string propertyName)
        {
            if (PropertyChanged != null)
            {
                PropertyChanged(this, new PropertyChangedEventArgs(propertyName));
            }
        }

        private void IncreaseButton_Click(object sender, RoutedEventArgs e)
        {
            Progress += 33;
        }

        private void DecreaseButton_Click(object sender, RoutedEventArgs e)
        {
            Progress -= 33;
        }


        #endregion

        #region Bindable Properties


        private ObservableCollection<BasicFeatureLayer> _layers = new ObservableCollection<BasicFeatureLayer>();
        public ObservableCollection<BasicFeatureLayer> Layers
        {
            get { return _layers; }
        }

 

        #endregion

        #region Commands

        private RelayCommand _selectToolCmd;
        public ICommand SelectToolCmd
        {
            get
            {
                if (_selectToolCmd == null)
                {
                    Console.WriteLine("SelectToolCmd called!");
                    _selectToolCmd = new RelayCommand(() => FrameworkApplication.SetCurrentToolAsync(_selectToolID), () => { return MapView.Active != null; });
                }
                return _selectToolCmd;
            }
        }

        private bool _selectToolActive = false;
        public bool SelectToolActive
        {
            get { return _selectToolActive; }
            set
            {
                SetProperty(ref _selectToolActive, true, () => SelectToolActive);
            }
        }

        /// <summary>
        /// Show the DockPane.
        /// </summary>
        internal static void Show()
        {
            DockPane pane = FrameworkApplication.DockPaneManager.Find(_dockPaneID);
            if (pane == null)
                return;

            pane.Activate();
        }

        #endregion

        #region Event Handlers


        private void OnActiveToolChanged(ToolEventArgs args)
        {
            SetProperty(ref _selectToolActive, (args.CurrentID == _selectToolID), () => SelectToolActive);
        }

        #endregion

        // <summary>
        /// Used to persist the state of the selected layer and object ID for a given map.
        /// </summary>
        internal class SelectedLayerInfo
        {
            public SelectedLayerInfo() { }
            public SelectedLayerInfo(BasicFeatureLayer selectedLayer, long? selectedOID)
            {
                SelectedLayer = selectedLayer;
                SelectedOID = selectedOID;
            }

            public BasicFeatureLayer SelectedLayer { get; set; }

            public long? SelectedOID { get; set; }
        }

        /// <summary>
        /// Text shown near the top of the DockPane.
        /// </summary>
        private string _heading = "Address Points";
        public string Heading
        {
            get { return _heading; }
            set
            {
                SetProperty(ref _heading, value, () => Heading);
            }
        }
    }

    /// <summary>
    /// Button implementation to show the DockPane.
    /// </summary>
    internal class AddressPointDockPane_ShowButton : Button
    {
        protected override void OnClick()
        {
            AddressPointDockPaneViewModel.Show();
        }
    }
}
