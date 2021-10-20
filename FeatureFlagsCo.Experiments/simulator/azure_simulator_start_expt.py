from datetime import datetime
from azure_service_bus.send_consume import AzureSender
from config.config_handling import get_config_value
from azure.servicebus import ServiceBusClient
import logging

logger = logging.getLogger('azure_simulator_start_expt')
logger.setLevel(logging.INFO)

CONN_STR = 'Endpoint=sb://ffc-ce2-dev.servicebus.chinacloudapi.cn/;SharedAccessKeyName=normal_send_receive;SharedAccessKey=aZep2SIj/kfLSy83lTkDodgwu7mlXvqYdk2weVvjXzk='


if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%m-%d %H:%M')
    redis_host = get_config_value('redis', 'redis_host')
    redis_port = get_config_value('redis', 'redis_port')
    redis_passwd = get_config_value('redis', 'redis_passwd')
    topic_1 = get_config_value('p1', 'topic_Q1')
    origin_1 = get_config_value('p1', 'subscription_Q1')
    topic_4 = get_config_value('p3', 'topic_Q4')
    origin_4 = get_config_value('p3', 'subscription_Q4')
    topic_5 = get_config_value('p3', 'topic_Q5')
    origin_5 = get_config_value('p3', 'subscription_Q5')

    bus = ServiceBusClient.from_connection_string(
        conn_str=CONN_STR, logging_enable=True)
    with bus:
        # Expt1
        # Q1 start
        Q1_START = {
            "ExptId": 'FF__38__48__103__PayButton_exp1',
            "IterationId": "2",
            "EnvId": "103",
            "FlagId": "FF__38__48__103__PayButton",
            "BaselineVariation": "1",
            "Variations": ["1", "2", "3"],
            "EventName": "ButtonPayTrack",
            'EventType': 1,
            'CustomEventTrackOption': 1,
            "StartExptTime": "2021-09-20T21:00:00.123456",
            "EndExptTime": ""
        }
        AzureSender(None, redis_host, redis_port, redis_passwd).send(
            bus, topic_1, origin_1, Q1_START)
        for group in range(1, 4):
            events = []
            for user in range(1000):
                # Q4
                Q4 = {
                    "RequestPath": "index/paypage",
                    "FeatureFlagId": "FF__38__48__103__PayButton",
                    "EnvId": "103",
                    "AccountId": "38",
                    "ProjectId": "48",
                    "FeatureFlagKeyName": "PayButton",
                    "UserKeyId": "u_group"+str(group)+"_"+str(user)+"@testliang.com",
                    "FFUserName": "u_group"+str(group)+"_"+str(user),
                    "VariationLocalId": str(group),
                    "VariationValue": "Small-Button",
                    "TimeStamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "phoneNumber": "135987652543"
                }
                events.append(Q4)
            AzureSender(None, redis_host, redis_port, redis_passwd).send(
                bus, topic_4, origin_4, *events)

        for group in range(1, 4):
            events = []
            for user in range(1000 - 200*group):
                Q5 = {
                    "Route": "index",
                    "Secret": "YjA1LTNiZDUtNCUyMDIxMDkwNDIyMTMxNV9fMzhfXzQ4X18xMDNfX2RlZmF1bHRfNzc1Yjg=",
                    "TimeStamp":  datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "Type": "CustomEvent",
                    "EventName": "ButtonPayTrack",
                    "NumericValue": 1,
                    "User": {
                            "FFUserName": "u_group"+str(group)+"_"+str(user),
                            "FFUserEmail": "u_group"+str(group)+"_"+str(user)+"@testliang.com",
                            "FFUserCountry": "China",
                            "FFUserKeyId": "u_group"+str(group)+"_"+str(user)+"@testliang.com",
                            "FFUserCustomizedProperties": [
                                {
                                    "Name": "age",
                                    "Value": "16"
                                }
                            ]
                    },
                    "ApplicationType": "Javascript",
                    "CustomizedProperties": [
                        {
                            "Name": "age",
                            "Value": "16"
                        }
                    ],
                    "ProjectId": "48",
                    "EnvironmentId": "103",
                    "AccountId": "38"
                }
                events.append(Q5)
            AzureSender(None, redis_host, redis_port, redis_passwd).send(
                bus, topic_5, origin_5, *events)
