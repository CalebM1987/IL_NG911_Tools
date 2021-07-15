using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using ArcGIS.Desktop.Mapping;
using ArcGIS.Core.Data;
using ArcGIS.Core.Geometry;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Threading.Tasks;


namespace CreateNG911Features
{
    class Utils
    {
        public const String RoadCenterlines = @"C:\Users\calebma\Documents\IL_911\IL_NG911_Tools\test_env\NG911_Schemas.gdb\NG911_Tables";


        /// <summary>
        /// utility function to enable an action to run on the UI thread (if not already)
        /// </summary>
        /// <param name="action">the action to execute</param>
        /// <returns></returns>
        internal static Task RunOnUIThread(Action action)
        {
            if (OnUIThread)
            {
                action();
                return Task.FromResult(0);
            }
            else
                return Task.Factory.StartNew(action, System.Threading.CancellationToken.None, TaskCreationOptions.None, QueuedTask.UIScheduler);
        }

        /// <summary>
        /// determines if the application is currently on the UI thread
        /// </summary>
        private static bool OnUIThread
        {
            get
            {
                if (FrameworkApplication.TestMode)
                    return QueuedTask.OnWorker;
                else
                    return System.Windows.Application.Current.Dispatcher.CheckAccess();
            }
        }
    }
}
