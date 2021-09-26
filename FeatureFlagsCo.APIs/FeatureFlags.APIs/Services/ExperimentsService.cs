﻿using FeatureFlags.APIs.Models;
using FeatureFlags.APIs.ViewModels;
using FeatureFlags.APIs.ViewModels.Experiments;
using FeatureFlagsCo.MQ;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Dynamic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;

namespace FeatureFlags.APIs.Services
{
    public interface IExperimentsService
    {
        Task ArchiveExperiment(string experimentId);
        Task<ExperimentQueryViewModel> CreateExperiment(ExperimentQueryViewModel param);
        Task<ExperimentIteration> StartIteration(int envId, string experimentId);
        Task<ExperimentIteration> StopIteration(int envId, string exptId, string iterationId);
        Task<string> GetEnvironmentEvents(int envId, MetricTypeEnum metricType, string lastItem = "", string searchText = "", int pageSize = 20);
        Task<List<ExperimentResultViewModel>> GetExperimentResult(ExperimentQueryViewModel param);
    }

    public class ExperimentsService: IExperimentsService
    {
        private readonly IOptions<MySettings> _mySettings;
        private readonly INoSqlService _noSqlDbService;
        private readonly IInsighstMqService _insightsService;

        public ExperimentsService(
            INoSqlService noSqlDbService,
            IInsighstMqService insightsService,
            IOptions<MySettings> mySettings)
        {
            _noSqlDbService = noSqlDbService;
            _insightsService = insightsService;
            _mySettings = mySettings;
        }


        public async Task ArchiveExperiment(string experimentId)
        {
            var experiment = await _noSqlDbService.GetExperimentByIdAsync(experimentId);
            if (experiment != null)
            {
                // If the experiment has active iteration
                experiment.Iterations.ForEach(i => {
                    if (i.EndTime.HasValue && i.EndTime.Value > DateTime.MinValue) 
                    {
                        var message = new ExperimentIterationMessageViewModel
                        {
                            ExptId = experiment.Id,
                            EnvId = experiment.EnvId,
                            IterationId = i.Id,
                            StartExptTime = i.StartTime.ToString("yyyy-MM-ddTHH:mm:ss.ffffff"),
                            EndExptTime = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.ffffff"),
                            EventName = experiment.EventName,
                            Flag = new ExperimentFeatureFlagViewModel
                            {
                                Id = experiment.Flag.Id,
                                BaselineVariation = experiment.Flag.BaselineVariation,
                                Variations = experiment.Flag.Variations
                            }
                        };

                        // TODO send message to Q1
                    }
                });


                await _noSqlDbService.ArchiveExperimentAsync(experimentId);
            };
        }

        public async Task<ExperimentQueryViewModel> CreateExperiment(ExperimentQueryViewModel param)
        {
            var experiment = await _noSqlDbService.GetExperimentByFeatureFlagAndEvent(param.Flag.Id, param.EventName);

            if (experiment == null)
            {
                // create experiment in db
                experiment = new Experiment
                {
                    EnvId = param.EnvId,
                    EventName = param.EventName,
                    Iterations = new List<ExperimentIteration>(),
                    Flag = new ExperimentFeatureFlag
                    {
                        Id = param.Flag.Id,
                        BaselineVariation = param.Flag.BaselineVariation,
                        Variations = param.Flag.Variations
                    }
                };

                experiment = await _noSqlDbService.CreateExperimentAsync(experiment);
                
            }

            param.ExptId = experiment._Id;
            
            return param;
        }


        public async Task<ExperimentIteration> StartIteration(int envId, string experimentId)
        {
            // create experiment in db
            var experiment = await _noSqlDbService.GetExperimentByIdAsync(experimentId);

            if (experiment != null)
            {
                var iteration = new ExperimentIteration
                {
                    Id = Guid.NewGuid().ToString(),
                    StartTime = DateTime.UtcNow,
                    // EndTime, Don't need set end time as this is a start experiment signal
                    Results = new List<IterationResult>()
                };

                if (experiment.Iterations == null) 
                {
                    experiment.Iterations = new List<ExperimentIteration>();
                }

                experiment.Iterations.ForEach(i => i.EndTime = DateTime.UtcNow);

                experiment.Iterations.Add(iteration);

                await _noSqlDbService.UpsertExperimentAsync(experiment);

                var message = new ExperimentIterationMessageViewModel
                {
                    ExptId = experiment.Id,
                    EnvId = envId,
                    IterationId = iteration.Id,
                    StartExptTime = iteration.StartTime.ToString("yyyy-MM-ddTHH:mm:ss.ffffff"),
                    EventName = experiment.EventName,
                    Flag = new ExperimentFeatureFlagViewModel 
                    {
                        Id = experiment.Flag.Id,
                        BaselineVariation = experiment.Flag.BaselineVariation,
                        Variations = experiment.Flag.Variations
                    }
                };

                // TODO send message to Q1

                return iteration;
            }      

            return null;
        }

        public async Task<ExperimentIteration> StopIteration(int envId, string experimentId, string iterationId)
        {
            // create experiment in db
            var experiment = await _noSqlDbService.GetExperimentByIdAsync(experimentId);

            if (experiment != null)
            {
                var iteration = experiment.Iterations.Find(i => i.Id == iterationId);
                iteration.EndTime = DateTime.UtcNow;

                await _noSqlDbService.UpsertExperimentAsync(experiment);

                var message = new ExperimentIterationMessageViewModel
                {
                    ExptId = experiment.Id,
                    EnvId = envId,
                    IterationId = iteration.Id,
                    StartExptTime = iteration.StartTime.ToString("yyyy-MM-ddTHH:mm:ss.ffffff"),
                    EndExptTime = iteration.EndTime.Value.ToString("yyyy-MM-ddTHH:mm:ss.ffffff"),
                    EventName = experiment.EventName,
                    Flag = new ExperimentFeatureFlagViewModel
                    {
                        Id = experiment.Flag.Id,
                        BaselineVariation = experiment.Flag.BaselineVariation,
                        Variations = experiment.Flag.Variations
                    }
                };

                // TODO send message to Q1


                return iteration;
            }

            return null;
        }

        public async Task<List<ExperimentResultViewModel>> GetExperimentResult(ExperimentQueryViewModel param)
        {
            string experimentationHost = _mySettings.Value.ExperimentsServiceHost;

            using (var client = new HttpClient())
            {
                HttpContent content = new StringContent(JsonConvert.SerializeObject(param));
                content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/json");

                //由HttpClient发出异步Post请求
                HttpResponseMessage res = await client.PostAsync($"{experimentationHost}/api/nosdk", content);
                if (res.StatusCode == System.Net.HttpStatusCode.OK)
                {
                    var result = await res.Content.ReadAsStringAsync();
                    return JsonConvert.DeserializeObject<List<ExperimentResultViewModel>>(result);
                }
                return new List<ExperimentResultViewModel>();
            }
        }

        public async Task<string> GetEnvironmentEvents(int envId, MetricTypeEnum metricType, string lastItem = "", string searchText = "", int pageSize = 20)
        {
            string esHost = _mySettings.Value.ElasticSearchHost;
            string indexTarget = "experiments";

            dynamic envIdMatch = new ExpandoObject();
            (envIdMatch as IDictionary<string, object>)["EnvironmentId.keyword"] = $"{envId}";

            dynamic boolClause = new ExpandoObject();
            boolClause.must = new List<dynamic>()
            {
                new {
                    match = new {
                        Type = "CustomEvent"
                    }
                },
                new {
                    match = envIdMatch
                },
            };

            if (!string.IsNullOrWhiteSpace(searchText)) 
            {
                boolClause.must.Add(new
                {
                    query_string = new
                    {
                        query = $"*{searchText}*",
                        default_field = "EventName"
                    }
                });
            }

            var compositeEO = new ExpandoObject();
            (compositeEO as IDictionary<string, object>)["sources"] = new List<dynamic>() {
                            new {
                                EventName = new {
                                    terms = new {
                                        field = "EventName.keyword"
                                    }
                                }
                            }
                        };


            (compositeEO as IDictionary<string, object>)["size"] = pageSize;

            if (!string.IsNullOrWhiteSpace(lastItem)) 
            {
                (compositeEO as IDictionary<string, object>)["after"] = new { 
                    EventName = lastItem
                };
            }

            var aggsEO = new
            {
                keys = new { 
                    composite = compositeEO
                }
            };

            dynamic queryEO = new ExpandoObject();
            (queryEO as IDictionary<string, object>)["bool"] = boolClause;

            dynamic sortEO = new ExpandoObject();
            (sortEO as IDictionary<string, object>)["EventName.keyword"] = new
            {
                order = "asc"
            };

            var body = new
            {
                size = 0,
                query = queryEO,
                sort = new List<dynamic> { sortEO },
                aggs = aggsEO
            };

            // to see how to create a query to fetch unique values, ref https://www.getargon.io/docs/articles/elasticsearch/unique-values.html

            using (var client = new HttpClient())
            {
                HttpContent content = new StringContent(JsonConvert.SerializeObject(body));
                content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/json");

                if (esHost.Contains("@")) // esHost contains username and password 
                {
                    var startIndex = esHost.LastIndexOf("/") + 1;
                    var endIndex = esHost.LastIndexOf("@");
                    var credential = esHost.Substring(startIndex, endIndex - startIndex).Split(":");
                    var userName = credential[0];
                    var password = credential[1];

                    esHost = esHost.Substring(0, startIndex) + esHost.Substring(endIndex + 1);

                    client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
                                                "Basic", Convert.ToBase64String(System.Text.ASCIIEncoding.ASCII.GetBytes($"{userName}:{password}")));
                }

                //由HttpClient发出异步Post请求
                HttpResponseMessage res = await client.PostAsync($"{esHost}/{indexTarget}/_search", content);
                if (res.StatusCode == System.Net.HttpStatusCode.OK)
                {
                    return await res.Content.ReadAsStringAsync();
                }
                return null;
            }
        }
    }
}
