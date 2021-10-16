﻿using System;
using System.Collections.Generic;

namespace FeatureFlagsCo.MQ
{
    public class ExperimentMessageModel
    {
        public string Route { get; set; }
        public string Secret { get; set; }
        public string TimeStamp { get; set; }
        public string Type { get; set; }
        public string EventName { get; set; }
        public float NumericValue { get; set; }
        public MqUserInfo User { get; set; }
        public string AppType { get; set; }
        public List<MqCustomizedProperty> CustomizedProperties { get; set; }
        public string ProjectId { get; set; }
        public string EnvironmentId { get; set; }
        public string AccountId { get; set; }
    }
}
