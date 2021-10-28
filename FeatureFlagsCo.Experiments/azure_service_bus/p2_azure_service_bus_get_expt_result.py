from time import sleep

from opencensus.ext.azure.log_exporter import AzureLogHandler
from config.config_handling import get_config_value
import logging
import numpy as np
import scipy as sp
from scipy import stats
from datetime import datetime, timedelta
import math
import pandas as pd

from azure_service_bus.send_consume import AzureReceiver

p2_logger = logging.getLogger('p2_azure_service_bus_get_expt_result')
p2_logger.addHandler(AzureLogHandler(
    connection_string=get_config_value('azure', 'insignt_conn_str')))
p2_logger.setLevel(logging.INFO)


class P2AzureGetExptResultReceiver(AzureReceiver):
    def __init__(self,
                 sb_host,
                 sb_sas_policy,
                 sb_sas_key,
                 redis_host='localhost',
                 redis_port='6379',
                 redis_passwd=None,
                 wait_timeout=30.0):
        super().__init__(sb_host, sb_sas_policy, sb_sas_key,
                         redis_host, redis_port, redis_passwd)
        self._last_expt_id = ''
        self._wait_timeout = wait_timeout

    # cal Confidence interval
    def __mean_confidence_interval(self, data, confidence=0.95):
        a = 1.0 * np.array(data)
        n = len(a)
        m, se = np.mean(a), sp.stats.sem(a)
        h = se * sp.stats.t.ppf((1 + confidence) / 2., n - 1)
        return m, m - h, m + h

    # cal Expt Result from list of FlagsEvents and list of CustomEvents:
    def __calc_experiment_result(self, expt, expt_id, list_ff_events, list_user_events):
        # User's flags event aggregation, if not empty
        if list_ff_events:
            df_ff_events = pd.DataFrame(list_ff_events)
            ff_events_agg = df_ff_events.sort_values('TimeStamp').groupby(
                'UserKeyId').last().reset_index().to_dict('records')
        else:
            ff_events_agg = []
        # User's custom event aggregation, if not empty
        if list_user_events:
            df_user_events = pd.DataFrame(list_user_events)
            user_events_agg = df_user_events.sort_values('TimeStamp').groupby(
                'UserKeyId').last().reset_index().to_dict('records')
        else:
            user_events_agg = []
        # Stat of Flag
        var_baseline = expt['BaselineVariation']
        dict_var_user = {}
        dict_var_occurence = {}

        # dictionary {
        #              'Var1' : Number_of_flag_event,
        #              'Var2' : Number_of_flag_event,
        #               ....  : ....
        #            }
        for item in ff_events_agg:
            value = item['VariationLocalId']
            user = item['UserKeyId']
            if value not in list(dict_var_occurence.keys()):
                dict_var_occurence[value] = 1
                dict_var_user[value] = [user]
            else:
                dict_var_occurence[value] = dict_var_occurence[value] + 1
                dict_var_user[value] = dict_var_user[value] + [user]
        p2_logger.info('dictionary of flag var:occurence')
        p2_logger.info(dict_var_occurence)

        # dictionary {
        #              'Var1' : list_of_unique_user,
        #              'Var2' : list_of_unique_user,
        #               ....  : ....
        #            }
        for item in dict_var_user.keys():
            dict_var_user[item] = list(set(dict_var_user[item]))

        # dictionary {
        #              'Var1' : Number_of_custom_event,
        #              'Var2' : Number_of_custom_event,
        #               ....  : ....
        #            }
        dict_expt_occurence = {}
        for item in user_events_agg:
            user = item['UserKeyId']
            for it in dict_var_user.keys():
                if user in dict_var_user[it]:
                    if it not in list(dict_expt_occurence.keys()):
                        dict_expt_occurence[it] = 1
                    else:
                        dict_expt_occurence[it] = 1 + \
                            dict_expt_occurence[it]
        p2_logger.info('dictionary of expt var:occurence')
        p2_logger.info(dict_expt_occurence)

        # list of results by flag-variation
        output = []
        for var in expt['Variations']:
            if var not in dict_var_occurence.keys():
                output.append({'variation': var,
                               'conversion': -1,
                               'uniqueUsers': -1,
                               'conversionRate': -1,
                               'changeToBaseline': -1,
                               'confidenceInterval': [-1, -1],
                               'pValue': -1,
                               'isBaseline': True if var_baseline == var else False,
                               'isWinner': False,
                               'isInvalid': True
                               })
        # If  (baseline variation usage = 0) or (baseline variation customer event = 0 )
        if var_baseline not in list(dict_var_occurence.keys()) or \
                var_baseline not in dict_expt_occurence.keys():
            # output only the flag-variation used.
            for item in dict_var_occurence.keys():
                if item in dict_expt_occurence.keys():
                    dist_item = [1 for i in range(dict_expt_occurence[item])] + [
                        0 for i in range(dict_var_occurence[item] - dict_expt_occurence[item])]
                    rate, min, max = self.__mean_confidence_interval(
                        dist_item)
                    if math.isnan(min) or math.isnan(max):
                        confidenceInterval = [-1, -1]
                    else:
                        confidenceInterval = [0 if round(min, 3) < 0 else round(
                            min, 3), 1 if round(max, 3) > 1 else round(max, 3)]
                    pValue = -1
                    output.append({'variation': item,
                                   'conversion': dict_expt_occurence[item],
                                   'uniqueUsers': dict_var_occurence[item],
                                   'conversionRate': round(rate, 3),
                                   'changeToBaseline': -1,
                                   'confidenceInterval': confidenceInterval,
                                   'pValue': -1,
                                   'isBaseline': True if var_baseline == item else False,
                                   'isWinner': False,
                                   'isInvalid': True
                                   })
                else:
                    output.append({'variation': item,
                                   'conversion': 0,
                                   'uniqueUsers': dict_var_occurence[item],
                                   'conversionRate': 0,
                                   'changeToBaseline': -1,
                                   'confidenceInterval': [-1, -1],
                                   'pValue': -1,
                                   'isBaseline': True if
                                   var_baseline == item else False,
                                   'isWinner': False,
                                   'isInvalid': True
                                   })
        else:
            BaselineRate = dict_expt_occurence[var_baseline] / \
                dict_var_occurence[var_baseline]
            # Preprare Baseline data sample distribution for Pvalue Calculation
            dist_baseline = [1 for i in range(dict_expt_occurence[var_baseline])] + [
                0 for i in range(dict_var_occurence[var_baseline]
                                 - dict_expt_occurence[var_baseline])]
            for item in dict_var_occurence.keys():
                if item in dict_expt_occurence.keys():
                    dist_item = [1 for i in range(dict_expt_occurence[item])] + [
                        0 for i in range(dict_var_occurence[item] - dict_expt_occurence[item])]
                    rate, min, max = self.__mean_confidence_interval(
                        dist_item)
                    if math.isnan(min) or math.isnan(max):
                        confidenceInterval = [-1, -1]
                    else:
                        confidenceInterval = [0 if round(min, 2) < 0 else round(
                            min, 2), 1 if round(max, 2) > 1 else round(max, 2)]
                    pValue = round(
                        1 - stats.ttest_ind(dist_baseline, dist_item).pvalue, 2)
                    output.append({'variation': item,
                                   'conversion': dict_expt_occurence[item],
                                   'uniqueUsers': dict_var_occurence[item],
                                   'conversionRate': round(rate, 3),
                                   'changeToBaseline': round(rate, 3) - round(BaselineRate, 3),
                                   'confidenceInterval': confidenceInterval,
                                   'pValue': -1 if math.isnan(pValue) else pValue,
                                   'isBaseline': True if var_baseline == item else False,
                                   'isWinner': False,
                                   'isInvalid': True if (pValue < 0.95)
                                   or math.isnan(pValue) else False
                                   })
                else:
                    output.append({'variation': item,
                                   'conversion': 0,
                                   'uniqueUsers': dict_var_occurence[item],
                                   'conversionRate': 0,
                                   'changeToBaseline': -1,
                                   'confidenceInterval': [-1, -1],
                                   'pValue': -1,
                                   'isBaseline': True if var_baseline == item else False,
                                   'isWinner': False,
                                   'isInvalid': True
                                   })
            # Get winner variation
            listValid = [output.index(
                item) for item in output if not item['isInvalid']]
            # If at least one variation is valid:
            if len(listValid) != 0:
                dictValid = {}
                for index in listValid:
                    dictValid[index] = output[index]['conversionRate']
                maxRateIndex = [k for k, v in sorted(
                    dictValid.items(), key=lambda item: item[1])][-1]
                # when baseline has the highest conversion rate
                if output[maxRateIndex]['changeToBaseline'] > 0:
                    output[maxRateIndex]['isWinner'] = True
        p2_logger.info('ExptResults:')
        p2_logger.info(output)
        # result to send to rabbitmq
        output_to_mq = {
            'ExperimentId': expt_id,
            'IterationId': expt['IterationId'],
            'StartTime': expt['StartExptTime'],
            'EndTime': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
            'Results': output
        }
        return output_to_mq

    def __parse_event_from_redis(self, expt, fmt):
        ExptStartTime = datetime.strptime(expt['StartExptTime'], fmt)
        ExptEndTime = None
        flag_id = expt['FlagId']
        event_name = expt['EventName']
        env_id = expt['EnvId']
        env_ff_id = '%s_%s' % (env_id, flag_id)
        env_event_id = '%s_%s' % (env_id, event_name)
        # Get list of events from Redis
        value_events_ff = self.redis_get(env_ff_id)
        list_ff_events = value_events_ff if value_events_ff else []
        value_user_events = self.redis_get(env_event_id)
        list_user_events = value_user_events if value_user_events else []
        # Filter Event according to Experiment StartTime
        list_ff_events = [ff_event for ff_event in list_ff_events if datetime.strptime(
            ff_event['TimeStamp'], fmt) >= ExptStartTime]
        list_user_events = [user_event for user_event in list_user_events if datetime.strptime(
            user_event['TimeStamp'], fmt) >= ExptStartTime]
        # Filter Event according to Experiment EndTime
        if expt['EndExptTime']:
            ExptEndTime = datetime.strptime(expt['EndExptTime'], fmt)
            list_ff_events = [ff_event for ff_event in list_ff_events if datetime.strptime(
                ff_event['TimeStamp'], fmt) <= ExptEndTime]
            list_user_events = [user_event for user_event in list_user_events if datetime.strptime(
                user_event['TimeStamp'], fmt) <= ExptEndTime]
        return expt, ExptStartTime, ExptEndTime, flag_id, event_name, env_id, \
            list_ff_events, list_user_events

    def __update_redis_with_EndExpt(self, list_ff_events, list_user_events,
                                    fmt, ExptStartTime, ExptEndTime, expt_id, expt):
        # Time to take decision to wait or not the upcomming event data
        para_delay_reception = 1
        para_wait_processing = 5
        # if empty list
        # If last event not received since N minutes, still wait M minutes after ExtpEndTime
        if list_ff_events and list_user_events:
            latest_ff_event_time = datetime.strptime(
                list_ff_events[-1]['TimeStamp'], fmt)
            latest_user_event_time = datetime.strptime(
                list_user_events[-1]['TimeStamp'], fmt)
            latest_event_end_time = max(
                [latest_ff_event_time, latest_user_event_time])
        elif not list_ff_events and not list_user_events:
            latest_event_end_time = ExptStartTime
        else:
            latest_event_end_time = datetime.strptime(
                (list_user_events + list_ff_events)[-1]['TimeStamp'], fmt)

        interval = ExptEndTime - latest_event_end_time
        # a delay to acept events after deadline
        if (interval > timedelta(minutes=para_delay_reception)) \
                and ((datetime.now() - ExptEndTime) < timedelta(minutes=para_wait_processing)):
            # send back exptId to Q2
            topic = get_config_value('p2', 'topic_Q2')
            subscription = get_config_value('p2', 'subscription_Q2')
            self.send(self._bus, topic, subscription, expt_id)
            p2_logger.info(
                'a delay to acept events after deadline of %r' % expt_id)
            p2_logger.info('#########send back to Q2 %r#########' % expt_id)
        # last event received within N minutes, no potential recepton delay, proceed data deletion
        else:
            # del expt
            self.redis_del(expt_id)
            # TODO move to somewhere
            # ACTION : Get from Redis > dict_flag_acitveExpts
            id = 'dict_ff_act_expts_%s_%s' % (
                expt['EnvId'], expt['FlagId'])
            dict_flag_acitveExpts = self.redis_get(id)
            if dict_flag_acitveExpts:
                dict_flag_acitveExpts[expt['FlagId']].remove(expt_id)
                self.redis_set(id, dict_flag_acitveExpts)
            # Update dict_flag_acitveExpts
            # ACTION : Get from Redis > dict_flag_acitveExpts
            id = 'dict_event_act_expts_%s_%s' % (
                expt['EnvId'], expt['EventName'])
            dict_customEvent_acitveExpts = self.redis_get(id)
            if dict_customEvent_acitveExpts:
                dict_customEvent_acitveExpts[expt['EventName']].remove(expt_id)
                self.redis_set(id, dict_customEvent_acitveExpts)
            # ACTION: Delete in Redis > list_FFevent related to FlagID
            # ACTION: Delete in Redis > list_Exptevent related to EventName
            p2_logger.info('Update info and delete stopped Experiment data')
            if dict_flag_acitveExpts and not dict_flag_acitveExpts.get(expt['FlagId'], None):
                id = '%s_%s' % (expt['EnvId'], expt['FlagId'])
                self.redis_del(id)
                # TODO move to somewhere
            if dict_customEvent_acitveExpts and not dict_customEvent_acitveExpts.get(expt['EventName'], None):
                id = '%s_%s' % (expt['EnvId'], expt['EventName'])
                self.redis_del(id)
                # TODO move to somewhere

            # del expt expired time
            dict_from_redis = self.redis_get('dict_expt_last_exec_time')
            if dict_from_redis:
                expt_last_exec_time = dict_from_redis.get(expt_id, None)
                if expt_last_exec_time:
                    dict_from_redis.pop(expt_id, None)
                    self.redis_set('dict_expt_last_exec_time', dict_from_redis)
            p2_logger.info('######### p2 %r finished #########' % expt_id)

    def handle_body(self, topic, body):
        starttime = datetime.now()
        expt_id = body
        value = self.redis_get(expt_id)
        fmt = '%Y-%m-%dT%H:%M:%S.%f'
        # Create or Get last_exec_time for each expt_id
        dict_from_redis = self.redis_get('dict_expt_last_exec_time')
        dict_expt_last_exec_time = dict_from_redis if dict_from_redis else {}
        last_exec_time = dict_expt_last_exec_time.get(expt_id, None)
        interval_to_wait = 0
        if expt_id == self._last_expt_id:
            interval_to_wait = self._wait_timeout
        elif not last_exec_time:
            pass
        else:
            interval = datetime.now() - datetime.strptime(last_exec_time, fmt)
            if interval.total_seconds() < self._wait_timeout:
                interval_to_wait = self._wait_timeout - interval.total_seconds()
        sleep(interval_to_wait)
        dict_expt_last_exec_time[expt_id] = datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S.%f")
        self.redis_set('dict_expt_last_exec_time', dict_expt_last_exec_time)
        self._last_expt_id = expt_id
        p2_logger.info("########p2 gets %r#########" % value)
        # If experiment info exist
        if value:
            # Parse experiment info
            expt, ExptStartTime, ExptEndTime, _, _, _, list_ff_events, list_user_events = \
                self.__parse_event_from_redis(value, fmt)

            # Start To Calculate Experiment Result
            # call function to calculate experiment result
            output_to_mq = self.__calc_experiment_result(
                expt, expt_id, list_ff_events, list_user_events)
            # send result to Q3
            topic = get_config_value('p2', 'topic_Q3')
            subscription = get_config_value('p2', 'subscription_Q3')
            self.send(self._bus, topic, subscription, output_to_mq)
            p2_logger.info('########p2 sends %r result to Q3#########' % expt_id)

            # experiment not finished
            if not expt['EndExptTime']:
                # send back exptId to Q2
                topic = get_config_value('p2', 'topic_Q2')
                subscription = get_config_value('p2', 'subscription_Q2')
                self.send(self._bus, topic, subscription, expt_id)
                p2_logger.info(
                    '#########p2 sends %r back to Q2########' % expt_id)
            # experiment finished
            else:
                # Decision to delete or not event related data
                self.__update_redis_with_EndExpt(list_ff_events, list_user_events,
                                                 fmt, ExptStartTime, ExptEndTime, expt_id, expt)
            endtime = datetime.now()
            delta = endtime - starttime
            p2_logger.info('######### p2 processing time in seconds: %r #########' %
                           delta.total_seconds())
